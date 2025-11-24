"""
Conductor API - Vercel deployment with full vector search
Integrates with conductor.supabase_query module for semantic search
Uses Vercel AI Gateway for embeddings
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)

            # Root endpoint
            if path == '/' or path == '':
                self.send_json_response(200, {
                    "name": "Conductor API",
                    "version": "1.0.0",
                    "status": "online",
                    "endpoints": {
                        "query": "POST /api/query",
                        "health": "GET /api/health",
                        "sessions": "GET /api/sessions"
                    }
                })
                return

            # Health check endpoint
            elif path == '/api/health':
                self.handle_health_check()
                return

            # Sessions list endpoint
            elif path == '/api/sessions':
                limit = int(query_params.get('limit', ['10'])[0])
                channel = query_params.get('channel', [None])[0]
                self.handle_sessions_list(limit, channel)
                return

            # Session detail endpoint
            elif path.startswith('/api/sessions/'):
                session_id = path.split('/')[-1]
                self.handle_session_detail(session_id)
                return

            # Not found
            else:
                self.send_json_response(404, {
                    "error": "Not Found",
                    "path": path
                })
                return

        except Exception as e:
            self.send_json_response(500, {
                "error": "Internal Server Error",
                "message": str(e)
            })

    def do_POST(self):
        """Handle POST requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            # Query endpoint - semantic search with Claude
            if path == '/api/query':
                self.handle_semantic_query()
                return
            
            # Method not allowed for other paths
            else:
                self.send_json_response(405, {
                    "error": "Method Not Allowed",
                    "path": path
                })
                return
                
        except Exception as e:
            self.send_json_response(500, {
                "error": "Internal Server Error",
                "message": str(e)
            })

    def handle_health_check(self):
        """Health check endpoint"""
        try:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL", "").strip()
            key = os.getenv("SUPABASE_ANON_KEY", "").strip()

            if not url or not key:
                self.send_json_response(503, {
                    "status": "degraded",
                    "supabase_connected": False,
                    "version": "1.0.0",
                    "error": "Supabase credentials not configured"
                })
                return

            # Try to connect to Supabase
            client = create_client(url, key)
            result = client.schema('vecs').from_('conductor_sessions').select('id').limit(1).execute()

            self.send_json_response(200, {
                "status": "healthy",
                "supabase_connected": True,
                "version": "1.0.0",
                "session_count": len(result.data) if result.data else 0
            })

        except Exception as e:
            self.send_json_response(503, {
                "status": "degraded",
                "supabase_connected": False,
                "version": "1.0.0",
                "error": str(e)
            })

    def handle_sessions_list(self, limit: int, channel: str = None):
        """List sessions endpoint"""
        try:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL", "").strip()
            key = os.getenv("SUPABASE_ANON_KEY", "").strip()

            if not url or not key:
                self.send_json_response(500, {
                    "error": "Supabase credentials not configured"
                })
                return

            client = create_client(url, key)
            limit = min(limit, 50)

            query = client.schema('vecs').from_('conductor_sessions').select('*')

            if channel:
                query = query.filter('metadata->>channel_name', 'eq', channel)

            result = query.limit(limit).execute()

            sessions = [
                {
                    "id": s['id'],
                    "metadata": s.get('metadata', {})
                }
                for s in result.data
            ]

            self.send_json_response(200, sessions)

        except Exception as e:
            self.send_json_response(500, {
                "error": str(e)
            })

    def handle_session_detail(self, session_id: str):
        """Session detail endpoint"""
        try:
            from supabase import create_client

            url = os.getenv("SUPABASE_URL", "").strip()
            key = os.getenv("SUPABASE_ANON_KEY", "").strip()

            if not url or not key:
                self.send_json_response(500, {
                    "error": "Supabase credentials not configured"
                })
                return

            client = create_client(url, key)
            result = client.schema('vecs').from_('conductor_sessions').select('*').eq('id', session_id).execute()

            if not result.data:
                self.send_json_response(404, {
                    "error": "Session not found",
                    "session_id": session_id
                })
                return

            session = result.data[0]
            self.send_json_response(200, {
                "id": session['id'],
                "metadata": session.get('metadata', {})
            })

        except Exception as e:
            self.send_json_response(500, {
                "error": str(e)
            })
    
    def handle_semantic_query(self):
        """Semantic search endpoint with Claude answer generation"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            query = data.get('query')
            match_count = data.get('match_count', 5)
            
            if not query:
                self.send_json_response(400, {
                    "error": "Query parameter is required"
                })
                return
            
            # Import at runtime to avoid cold start issues
            from conductor.supabase_query import query_vector_similarity
            from anthropic import Anthropic
            from openai import OpenAI
            
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            ai_gateway_key = os.getenv("AI_GATEWAY_API_KEY", "").strip()
            
            if not anthropic_key:
                self.send_json_response(500, {
                    "error": "Anthropic API key not configured"
                })
                return
            
            if not ai_gateway_key:
                self.send_json_response(500, {
                    "error": "AI Gateway API key not configured"
                })
                return
            
            # Step 1: Generate embedding using Vercel AI Gateway
            # Using OpenAI text-embedding-3-small with 384 dimensions (matches ChromaDB default)
            try:
                # Configure OpenAI client to use Vercel AI Gateway
                openai_client = OpenAI(
                    api_key=ai_gateway_key,
                    base_url="https://ai-gateway.vercel.sh/v1",
                )

                # Generate embedding with 384 dimensions to match existing data
                response = openai_client.embeddings.create(
                    model="openai/text-embedding-3-small",
                    input=query,
                    dimensions=384,
                    encoding_format="float",
                )

                query_embedding = response.data[0].embedding

            except Exception as embed_error:
                self.send_json_response(500, {
                    "error": "Failed to generate embedding",
                    "details": str(embed_error)
                })
                return
            
            # Step 2: Query Supabase vector search using the imported function
            try:
                results = query_vector_similarity(
                    query_embedding=query_embedding,
                    match_threshold=0.0,
                    match_count=match_count
                )
            except Exception as search_error:
                self.send_json_response(500, {
                    "error": "Vector search failed",
                    "details": str(search_error)
                })
                return
            
            # Step 3: Check if we got results
            if not results.get('documents') or not results['documents'][0]:
                self.send_json_response(200, {
                    "answer": "No relevant sessions found in the database.",
                    "sources": [],
                    "query": query
                })
                return
            
            # Step 4: Format context for Claude
            context_parts = []
            sources = []
            
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            
            for i, (doc, metadata) in enumerate(zip(documents, metadatas), 1):
                context_parts.append(f'<context id="{i}">')
                context_parts.append(f"Date: {metadata.get('date', 'Unknown')}")
                context_parts.append(f"Channel: {metadata.get('channel', 'Unknown')}")
                context_parts.append(f"Start Time: {metadata.get('start_time', 'Unknown')}")
                context_parts.append(f"Message Count: {metadata.get('message_count', 'Unknown')}")
                context_parts.append(f"File Count: {metadata.get('file_count', 'Unknown')}")
                context_parts.append("")
                context_parts.append(doc)
                context_parts.append("</context>")
                context_parts.append("")
                
                sources.append({
                    "date": metadata.get('date'),
                    "channel": metadata.get('channel'),
                    "message_count": metadata.get('message_count')
                })
            
            context = "\n".join(context_parts)
            
            # Step 5: Query Claude
            anthropic_client = Anthropic(api_key=anthropic_key)
            
            system_prompt = """You are a Real Estate Archives Assistant. Answer based ONLY on the provided context.
Cite the specific date, channel, and agent name for every claim. If the information is not in the context, say "I don't have information about that in the archives."
"""
            
            user_message = f"""Context from archives:

{context}

Question: {query}"""
            
            message = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            )
            
            # Extract answer
            answer = ""
            if message.content and len(message.content) > 0:
                text_parts = []
                for block in message.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
                answer = "\n".join(text_parts)
            else:
                answer = "No response from Claude."
            
            # Return response
            self.send_json_response(200, {
                "answer": answer,
                "sources": sources,
                "query": query,
                "retrieval_count": len(documents)
            })
            
        except json.JSONDecodeError:
            self.send_json_response(400, {
                "error": "Invalid JSON in request body"
            })
        except Exception as e:
            self.send_json_response(500, {
                "error": str(e),
                "type": type(e).__name__
            })

    def send_json_response(self, status_code: int, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_redirect(self, location: str):
        """Send redirect response"""
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()
