# Vercel AI Gateway Integration Guide

## Overview

This guide explains how to integrate the Conductor project with Vercel AI Gateway for production deployments. The AI Gateway provides:

- **Cost Optimization**: Route requests through multiple providers
- **Rate Limiting**: Built-in protection against quota exhaustion
- **Monitoring**: Track usage and performance metrics
- **High Availability**: Automatic failover between providers

## Your Gateway Configuration

- **Gateway Name**: `q-slack`
- **API Key**: `vck_10FUrzsEszbdp3k75TGQ0dWFLzGnwj9zePsTQaAwGzXVUOFYjB4728l2`
- **Provider**: Anthropic (Claude)
- **Base URL**: `https://ai-gateway.vercel.sh/v1`

## Quick Start

### 1. Environment Variables

Already configured in `.env`:
```bash
AI_GATEWAY_API_KEY=vck_10FUrzsEszbdp3k75TGQ0dWFLzGnwj9zePsTQaAwGzXVUOFYjB4728l2
```

### 2. Install OpenAI SDK (for AI Gateway)

```bash
source .venv/bin/activate
pip install openai
```

Or add to `requirements.txt`:
```
openai>=1.0.0
```

### 3. Basic Usage Example

```python
from openai import OpenAI
import os

# Initialize client with AI Gateway
client = OpenAI(
    api_key=os.getenv('AI_GATEWAY_API_KEY'),
    base_url='https://ai-gateway.vercel.sh/v1'
)

# Call Claude via gateway
response = client.chat.completions.create(
    model='anthropic/claude-sonnet-4',
    messages=[
        {'role': 'user', 'content': 'Analyze this Slack conversation...'}
    ],
    max_tokens=2048
)

print(response.choices[0].message.content)
```

## Integration with Conductor

### Create AI Gateway Client Module

**File**: `conductor/ai_gateway.py`

```python
"""
AI Gateway client for Conductor.

Provides Claude API access via Vercel AI Gateway with error handling,
retries, and structured logging.
"""

import os
import logging
from typing import List, Dict, Optional
from openai import OpenAI, APIError, RateLimitError

logger = logging.getLogger(__name__)


class AIGatewayClient:
    """Client for Vercel AI Gateway with Anthropic/Claude integration."""

    def __init__(self, api_key: Optional[str] = None, gateway_name: str = 'q-slack'):
        """
        Initialize AI Gateway client.

        Args:
            api_key: Vercel AI Gateway API key (defaults to AI_GATEWAY_API_KEY env var)
            gateway_name: Name of your gateway in Vercel (default: q-slack)
        """
        self.api_key = api_key or os.getenv('AI_GATEWAY_API_KEY')
        if not self.api_key:
            raise ValueError(
                "AI_GATEWAY_API_KEY environment variable not set. "
                "Get your key from: https://vercel.com/dashboard/ai"
            )

        self.gateway_name = gateway_name
        self.client = OpenAI(
            api_key=self.api_key,
            base_url='https://ai-gateway.vercel.sh/v1'
        )

        logger.info(f"AI Gateway client initialized (gateway: {gateway_name})")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = 'anthropic/claude-sonnet-4',
        max_tokens: int = 2048,
        temperature: float = 1.0,
        stream: bool = False
    ) -> str:
        """
        Send chat completion request via AI Gateway.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (default: anthropic/claude-sonnet-4)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            stream: Enable streaming responses

        Returns:
            Response content as string

        Raises:
            RateLimitError: If rate limit exceeded
            APIError: If API call fails
        """
        try:
            logger.info(f"Calling AI Gateway with {len(messages)} messages")

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )

            if stream:
                # Return generator for streaming
                return response

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            logger.info(f"AI Gateway call successful (tokens: {tokens_used})")
            return content

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise

        except APIError as e:
            logger.error(f"API error from gateway: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error calling AI Gateway: {e}")
            raise

    def analyze_session(self, session_text: str) -> str:
        """
        Analyze a Slack session using Claude via AI Gateway.

        Args:
            session_text: Full session transcript

        Returns:
            Analysis summary
        """
        messages = [
            {
                'role': 'user',
                'content': f"Analyze this Slack conversation and extract key insights:\n\n{session_text}"
            }
        ]

        return self.chat(messages, max_tokens=1024)
```

### Usage in Conductor Ingestion

**File**: `conductor/ingest.py` (example integration)

```python
from conductor.ai_gateway import AIGatewayClient

def process_session_with_ai(session: Session) -> str:
    """Process a session with AI analysis."""
    try:
        gateway = AIGatewayClient()
        analysis = gateway.analyze_session(session.transcript)
        logger.info(f"AI analysis completed for session {session.id}")
        return analysis
    except Exception as e:
        logger.error(f"Failed to analyze session {session.id}: {e}")
        return ""
```

## Deployment to Vercel

### Option 1: Via Vercel Dashboard

1. Go to your project in Vercel dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add new variable:
   - **Name**: `AI_GATEWAY_API_KEY`
   - **Value**: `vck_10FUrzsEszbdp3k75TGQ0dWFLzGnwj9zePsTQaAwGzXVUOFYjB4728l2`
   - **Environments**: Production, Preview, Development
4. Click **Save**
5. Redeploy your application

### Option 2: Via Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Link project
vercel link

# Add environment variable
vercel env add AI_GATEWAY_API_KEY

# When prompted, paste:
vck_10FUrzsEszbdp3k75TGQ0dWFLzGnwj9zePsTQaAwGzXVUOFYjB4728l2

# Select environments: Production, Preview, Development

# Deploy
vercel --prod
```

## Advanced Features

### Streaming Responses

For real-time feedback during long-running operations:

```python
from conductor.ai_gateway import AIGatewayClient

def stream_analysis(session_text: str):
    """Stream AI analysis in real-time."""
    gateway = AIGatewayClient()

    messages = [
        {'role': 'user', 'content': f"Analyze: {session_text}"}
    ]

    stream = gateway.chat(messages, stream=True)

    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='', flush=True)
```

### Provider Fallback

Configure automatic failover to backup providers:

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv('AI_GATEWAY_API_KEY'),
    base_url='https://ai-gateway.vercel.sh/v1'
)

response = client.chat.completions.create(
    model='anthropic/claude-sonnet-4',
    messages=[{'role': 'user', 'content': 'Hello'}],
    extra_body={
        'providerOptions': {
            'gateway': {
                'order': ['anthropic', 'vertex'],  # Try Anthropic, fallback to Vertex AI
                'timeout': 30000  # 30 second timeout
            }
        }
    }
)
```

## Monitoring & Analytics

View gateway usage in Vercel dashboard:

1. Go to https://vercel.com/dashboard/ai
2. Select your `q-slack` gateway
3. View metrics:
   - Total requests
   - Token usage
   - Response times
   - Error rates
   - Cost breakdown

## Testing

### Test AI Gateway Connection

```python
# test_ai_gateway.py
from conductor.ai_gateway import AIGatewayClient

def test_connection():
    """Test AI Gateway connectivity."""
    try:
        gateway = AIGatewayClient()

        response = gateway.chat([
            {'role': 'user', 'content': 'Say "Hello from q-slack gateway!"'}
        ])

        print(f"✅ AI Gateway working: {response}")
        return True

    except Exception as e:
        print(f"❌ AI Gateway error: {e}")
        return False

if __name__ == '__main__':
    test_connection()
```

Run test:
```bash
source .venv/bin/activate
python test_ai_gateway.py
```

## Troubleshooting

### Error: "Invalid API key"

**Solution**: Verify `AI_GATEWAY_API_KEY` is set correctly in `.env`

```bash
echo $AI_GATEWAY_API_KEY
# Should output: vck_10FUrzsEszbdp3k75TGQ0dWFLzGnwj9zePsTQaAwGzXVUOFYjB4728l2
```

### Error: "Gateway not found"

**Solution**: Check that gateway name matches in Vercel dashboard (should be `q-slack`)

### Error: "Rate limit exceeded"

**Solution**: Check gateway limits in Vercel dashboard. Upgrade plan if needed.

### Slow Responses

**Solution**:
- Check Vercel AI Gateway dashboard for latency metrics
- Consider enabling caching for repeated queries
- Use streaming for better perceived performance

## Cost Optimization

### Best Practices

1. **Use appropriate models**: Start with `claude-sonnet-4`, upgrade to `opus` only when needed
2. **Set max_tokens wisely**: Use lower values for summaries, higher for detailed analysis
3. **Cache results**: Store AI responses in Supabase to avoid redundant calls
4. **Batch processing**: Process multiple sessions in one call when possible

### Example: Cached Analysis

```python
from conductor.ai_gateway import AIGatewayClient
from conductor.supabase_query import get_supabase_client

def analyze_with_cache(session_id: str, session_text: str) -> str:
    """Analyze session with caching to reduce API calls."""
    supabase = get_supabase_client()

    # Check cache first
    result = supabase.table('ai_analysis_cache').select('analysis').eq('session_id', session_id).execute()

    if result.data:
        logger.info(f"Using cached analysis for {session_id}")
        return result.data[0]['analysis']

    # Not in cache - call AI Gateway
    gateway = AIGatewayClient()
    analysis = gateway.analyze_session(session_text)

    # Store in cache
    supabase.table('ai_analysis_cache').insert({
        'session_id': session_id,
        'analysis': analysis,
        'created_at': 'now()'
    }).execute()

    return analysis
```

## Security Notes

- ✅ API key is stored in environment variables (not in code)
- ✅ Key is gitignored via `.env`
- ✅ Vercel encrypts environment variables at rest
- ✅ Use different keys for dev/staging/production (create additional gateways in Vercel)

## Next Steps

1. ✅ Environment variables configured
2. ⏳ Create `conductor/ai_gateway.py` module
3. ⏳ Add `openai` to requirements.txt
4. ⏳ Integrate with ingestion pipeline
5. ⏳ Deploy to Vercel with environment variables
6. ⏳ Monitor usage in Vercel dashboard

## Additional Resources

- [Vercel AI Gateway Documentation](https://vercel.com/docs/ai/ai-gateway)
- [Anthropic Claude API Reference](https://docs.anthropic.com/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- Your Gateway: https://vercel.com/dashboard/ai (select `q-slack`)
