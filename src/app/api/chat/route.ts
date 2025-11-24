import { NextResponse } from 'next/server';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ConductorSource {
  date: string;
  channel: string;
  message_count: number;
}

interface ConductorQueryResponse {
  answer: string;
  sources: ConductorSource[];
  query: string;
  retrieval_count: number;
}

export const maxDuration = 60;

export async function POST(req: Request) {
  const requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substring(7);
  console.log('[' + requestId + '] Chat API route called');

  try {
    const requestBody = await req.json();
    const messages = requestBody.messages as ChatMessage[];
    console.log('[' + requestId + '] Received ' + messages.length + ' messages');

    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== 'user') {
      console.error('[' + requestId + '] No user message found');
      return NextResponse.json(
        { error: 'No user message found' },
        { status: 400 }
      );
    }

    const query = lastMessage.content;
    console.log('[' + requestId + '] Query: "' + query + '"');

    const apiUrl = new URL('/api/index', req.url);
    console.log('[' + requestId + '] Fetching from: ' + apiUrl.toString());

    const response = await fetch(apiUrl.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        match_count: 5
      }),
    });

    console.log('[' + requestId + '] Python API response status: ' + response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[' + requestId + '] Conductor API error: ' + response.status + ' - ' + errorText);
      throw new Error('Conductor API error: ' + response.statusText);
    }

    const data: ConductorQueryResponse = await response.json();
    console.log('[' + requestId + '] Got response with ' + ((data.sources && Array.isArray(data.sources)) ? data.sources.length : 0) + ' sources');

    let formattedContent = data.answer || 'No answer provided.';

    // FIX 1: Proper null check for sources
    if (data.sources && Array.isArray(data.sources) && data.sources.length > 0) {
      formattedContent += '\n\n---\n\n**Sources:**\n\n';
      data.sources.forEach((source, index) => {
        const sourceNum = index + 1;
        // Additional safety for source properties
        const channel = source?.channel || 'Unknown';
        const date = source?.date || 'Unknown';
        const messageCount = source?.message_count || 0;
        formattedContent += sourceNum + '. **' + channel + '** (' + date + ')\n';
        formattedContent += '   - ' + messageCount + ' messages\n\n';
      });
    }

    console.log('[' + requestId + '] Creating SSE streaming response');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // FIX 2: Correct SSE format with "data: " prefix and double newlines
          const messageStart = 'data: {"type":"message_start","id":"' + requestId + '","role":"assistant"}\n\n';
          controller.enqueue(encoder.encode(messageStart));

          const chunkSize = 50;
          for (let i = 0; i < formattedContent.length; i += chunkSize) {
            const chunk = formattedContent.substring(i, i + chunkSize);
            const escapedChunk = chunk.replace(/\n/g, '\\n').replace(/"/g, '\\"');
            // FIX 2: Correct SSE format
            const deltaEvent = 'data: {"type":"text-delta","textDelta":"' + escapedChunk + '"}\n\n';
            controller.enqueue(encoder.encode(deltaEvent));
            await new Promise(resolve => setTimeout(resolve, 10));
          }

          // FIX 2: Correct SSE format
          controller.enqueue(encoder.encode('data: {"type":"message_complete","finishReason":"stop"}\n\n'));

          console.log('[' + requestId + '] Stream completed successfully');
          controller.close();
        } catch (error) {
          console.error('[' + requestId + '] Error in stream:', error);
          // FIX 3: Send error as SSE event instead of crashing
          const errorEvent = 'data: {"type":"error","error":"' + (error instanceof Error ? error.message : 'Unknown error') + '"}\n\n';
          controller.enqueue(encoder.encode(errorEvent));
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('[' + requestId + '] Error querying Conductor:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to query Conductor' },
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
