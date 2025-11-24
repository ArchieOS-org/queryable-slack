import { NextResponse } from 'next/server';
import type { ConductorQueryResponse } from '@/lib/conductor-types';

export const maxDuration = 60;

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function POST(req: Request) {
  try {
    const { messages }: { messages: ChatMessage[] } = await req.json();

    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== 'user') {
      return NextResponse.json(
        { error: 'No user message found' },
        { status: 400 }
      );
    }

    const query = lastMessage.content;

    const conductorUrl = process.env.NEXT_PUBLIC_CONDUCTOR_API_URL || 'https://queryable-slack-uprf9bjfg-nsd97s-projects.vercel.app';
    const response = await fetch(`${conductorUrl}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        match_count: 5
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Conductor API error:', response.status, errorText);
      throw new Error(`Conductor API error: ${response.statusText}`);
    }

    const data: ConductorQueryResponse = await response.json();

    let formattedContent = data.answer;

    if (data.sources && data.sources.length > 0) {
      formattedContent += '\n\n---\n\n**Sources:**\n\n';
      data.sources.forEach((source, index) => {
        const sourceNum = index + 1;
        formattedContent += `${sourceNum}. **${source.channel}** (${source.date})\n`;
        formattedContent += `   - ${source.message_count} messages\n\n`;
      });
    }

    return NextResponse.json({
      id: Date.now().toString(),
      role: 'assistant',
      content: formattedContent,
      sources: data.sources,
      retrieval_count: data.retrieval_count,
    });

  } catch (error) {
    console.error('Error querying Conductor:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to query Conductor' },
      { status: 500 }
    );
  }
}
