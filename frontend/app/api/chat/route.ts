import { NextResponse } from 'next/server';
import type { ConductorQueryResponse } from '@/lib/conductor-types';

export const maxDuration = 60;

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

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

    const apiUrl = new URL('/api/query', req.url);
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
    console.log('[' + requestId + '] Got response with ' + (data.sources?.length || 0) + ' sources');

    let formattedContent = data.answer;

    if (data.sources && data.sources.length > 0) {
      formattedContent += '\n\n---\n\n**Sources:**\n\n';
      data.sources.forEach((source, index) => {
        const sourceNum = index + 1;
        formattedContent += sourceNum + '. **' + source.channel + '** (' + source.date + ')\n';
        formattedContent += '   - ' + source.message_count + ' messages\n\n';
      });
    }

    console.log('[' + requestId + '] Creating SSE streaming response');

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          const messageStart = '0:{"type":"message_start","id":"' + requestId + '","role":"assistant"}\n';
          controller.enqueue(encoder.encode(messageStart));

          const chunkSize = 50;
          for (let i = 0; i < formattedContent.length; i += chunkSize) {
            const chunk = formattedContent.substring(i, i + chunkSize);
            const escapedChunk = chunk.replace(/\n/g, '\\n').replace(/"/g, '\\"');
            const deltaEvent = '0:{"type":"text-delta","textDelta":"' + escapedChunk + '"}\n';
            controller.enqueue(encoder.encode(deltaEvent));
            await new Promise(resolve => setTimeout(resolve, 10));
          }

          controller.enqueue(encoder.encode('0:{"type":"message_complete","finishReason":"stop"}\n'));

          console.log('[' + requestId + '] Stream completed successfully');
          controller.close();
        } catch (error) {
          console.error('[' + requestId + '] Error in stream:', error);
          controller.error(error);
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
