"""
Conductor API - Vercel deployment with full vector search
Integrates with conductor.supabase_query module for semantic search
Uses Vercel AI Gateway for embeddings
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path for conductor package imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json


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
                    "version": "2.0.0",
                    "status": "online",
                    "endpoints": {
                        "query": "POST /api/query",
                        "health": "GET /api/health",
                        "sessions": "GET /api/sessions"
                    },
                    "query_parameters": {
                        "query": "Required - The search query text",
                        "match_count": "Optional - Number of results (default: 5)",
                        "person": "Optional - Filter by person name",
                        "address": "Optional - Filter by address",
                        "channel": "Optional - Filter by channel name",
                        "use_entity_detection": "Optional - Auto-detect entities (default: true)"
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
            if path == '/api/query' or path == '/api/index' or path == '/':
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

    
    def do_OPTIONS(self):
        """Handle CORS preflight OPTIONS requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

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
        """Semantic search endpoint with Claude answer generation and entity filtering"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            query = data.get('query')
            match_count = data.get('match_count', 5)

            # Entity filtering parameters (optional)
            filter_person = data.get('person')  # Filter by person name
            filter_address = data.get('address')  # Filter by address
            filter_channel = data.get('channel')  # Filter by channel
            use_entity_detection = data.get('use_entity_detection', True)  # Auto-detect entities

            if not query:
                self.send_json_response(400, {
                    "error": "Query parameter is required"
                })
                return

            # Import at runtime to avoid cold start issues
            from conductor.supabase_query import query_vector_similarity, query_with_entity_filter
            from conductor.deep_research_query import deep_research_query
            from conductor.query_classifier import classify_query, extract_entities
            from anthropic import Anthropic
            from openai import OpenAI
            import re

            # Step 0: Classify the query to determine processing mode
            classification = classify_query(query)
            
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
            
            # Step 1.5: Auto-detect entities from query if enabled
            detected_entities = []
            if use_entity_detection and not filter_person:
                detected_entities = extract_entities(query)
                # Use first detected entity as person filter if available
                if detected_entities and classification.entities_mentioned:
                    filter_person = classification.entities_mentioned[0]

            # Step 2: Use exhaustive deep research with multi-query + RRF fusion
            # Pass classification for adaptive parameters (boosted retrieval for analytical queries)
            try:
                # If entity filters provided, use entity-filtered search first
                entity_filtered_results = None
                if filter_person or filter_address or filter_channel:
                    try:
                        entity_filtered_results = query_with_entity_filter(
                            query_embedding=query_embedding,
                            match_threshold=0.0,
                            match_count=match_count * 2,  # Get more for entity filtering
                            person=filter_person,
                            address=filter_address,
                            channel=filter_channel,
                        )
                    except Exception as entity_err:
                        # Fall back to regular search if entity search fails
                        pass

                # Use deep research for comprehensive results
                results = deep_research_query(
                    query_text=query,
                    query_embedding=query_embedding,
                    deep_research_n_results=50,   # 50 per query variation (boosted to 75 for analytical)
                    max_final_results=40,          # 40 after RRF fusion (boosted to 60 for analytical)
                    num_query_variations=7,        # 7 diverse queries (boosted to 10 for analytical)
                    classification=classification  # Pass classification for adaptive behavior
                )

                # Merge entity-filtered results with deep research results
                if entity_filtered_results and entity_filtered_results.get('ids', [[]])[0]:
                    # Prepend entity-filtered results (higher priority)
                    merged_ids = entity_filtered_results['ids'][0] + results.get('ids', [[]])[0]
                    merged_docs = entity_filtered_results['documents'][0] + results.get('documents', [[]])[0]
                    merged_meta = entity_filtered_results['metadatas'][0] + results.get('metadatas', [[]])[0]
                    merged_dist = entity_filtered_results['distances'][0] + results.get('distances', [[]])[0]

                    # Deduplicate by ID, keeping first occurrence (entity-filtered)
                    seen_ids = set()
                    deduped = {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
                    for i, doc_id in enumerate(merged_ids):
                        if doc_id not in seen_ids:
                            seen_ids.add(doc_id)
                            deduped['ids'][0].append(doc_id)
                            deduped['documents'][0].append(merged_docs[i])
                            deduped['metadatas'][0].append(merged_meta[i])
                            deduped['distances'][0].append(merged_dist[i])
                    results = deduped

            except Exception as search_error:
                self.send_json_response(500, {
                    "error": "Deep research failed",
                    "details": str(search_error)
                })
                return
            
            # Step 4: Check if we got results
            if not results.get('documents') or not results['documents'][0]:
                self.send_json_response(200, {
                    "answer": "No relevant sessions found in the database.",
                    "sources": [],
                    "query": query
                })
                return
            
            # Step 5: Format context for Claude
            context_parts = []
            sources = []
            
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            
            for i, (doc, metadata) in enumerate(zip(documents, metadatas), 1):
                context_parts.append('<context id="' + str(i) + '">')
                context_parts.append('Date: ' + str(metadata.get('date', 'Unknown')))
                context_parts.append('Channel: ' + str(metadata.get('channel', 'Unknown')))
                context_parts.append('Start Time: ' + str(metadata.get('start_time', 'Unknown')))
                context_parts.append('Message Count: ' + str(metadata.get('message_count', 'Unknown')))
                context_parts.append('File Count: ' + str(metadata.get('file_count', 'Unknown')))
                context_parts.append("")
                context_parts.append(doc)
                context_parts.append("</context>")
                context_parts.append("")
                
                sources.append({
                    "date": metadata.get('date') or 'Unknown',
                    "channel": metadata.get('channel') or 'Unknown',
                    "message_count": metadata.get('message_count') or 0
                })
            
            context = "\n".join(context_parts)
            
            # Step 6: Query Claude with appropriate system prompt based on classification
            anthropic_client = Anthropic(api_key=anthropic_key)

            # Import system prompts and select based on query classification
            from conductor.prompt_refiner import (
                SYSTEM_PROMPT_SEARCH_AGENT,
                SYSTEM_PROMPT_ANALYTICAL_RESEARCHER,
            )

            # Select analytical prompt for complex queries, search agent for simple factual queries
            if classification.query_type in ("analytical", "comparative", "behavioral"):
                system_prompt = SYSTEM_PROMPT_ANALYTICAL_RESEARCHER
            else:
                system_prompt = SYSTEM_PROMPT_SEARCH_AGENT

            user_message = 'Context from archives:\n\n' + context + '\n\nQuestion: ' + query

            # Build API parameters
            api_params = {
                "model": "claude-opus-4-5-20251101",
                "max_tokens": 16384 if classification.requires_extended_thinking else 8192,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    }
                ],
            }

            # Enable extended thinking for analytical queries
            if classification.requires_extended_thinking:
                api_params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": classification.suggested_budget_tokens,
                }

            message = anthropic_client.messages.create(**api_params)

            # Extract answer (handle both regular text and thinking blocks)
            answer = ""
            if message.content and len(message.content) > 0:
                text_parts = []
                for block in message.content:
                    # Skip thinking blocks, only include text blocks
                    if hasattr(block, "text") and block.type == "text":
                        text_parts.append(block.text)
                answer = "\n".join(text_parts)
            else:
                answer = "No response from Claude."
            
            # Return response with classification and entity filtering metadata
            self.send_json_response(200, {
                "answer": answer,
                "sources": sources,
                "query": query,
                "retrieval_count": len(documents),
                "classification": {
                    "query_type": classification.query_type,
                    "extended_thinking": classification.requires_extended_thinking,
                    "entities_detected": classification.entities_mentioned,
                    "analysis_dimensions": classification.analysis_dimensions,
                },
                "entity_filters": {
                    "person": filter_person,
                    "address": filter_address,
                    "channel": filter_channel,
                    "auto_detected": detected_entities,
                }
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
