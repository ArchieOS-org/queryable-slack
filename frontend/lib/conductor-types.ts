/**
 * TypeScript types for Conductor API responses
 */

export interface ConductorQueryRequest {
  query: string;
  match_count?: number;
}

export interface ConductorSource {
  date: string;
  channel: string;
  message_count: number;
}

export interface ConductorQueryResponse {
  answer: string;
  sources: ConductorSource[];
  query: string;
  retrieval_count: number;
}

export interface ConductorSession {
  id: string;
  metadata: {
    date?: string;
    channel?: string;
    channel_name?: string;
    start_time?: string;
    end_time?: string;
    message_count?: number;
    file_count?: number;
    conversation_type?: string;
  };
}
