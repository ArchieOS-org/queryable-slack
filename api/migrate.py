"""
Standalone migration endpoint for Vercel.
Uses BaseHTTPRequestHandler as per Context7 best practices.
"""

import os
import json
import logging
from http.server import BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress tokenizers parallelism warning
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')


def _convert_to_pooler_url(db_url: str) -> str:
    """
    Convert direct Supabase connection URL to connection pooler URL.
    Context7 best practice: Use connection pooler for serverless/Vercel.
    
    Tries multiple approaches:
    1. If already using pooler, return as-is
    2. Try to convert to pooler URL with correct format
    3. If conversion fails, add IPv4 preference to direct connection
    """
    import re
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
    
    # Parse the connection URL
    parsed = urlparse(db_url)
    
    # Check if already using pooler - return as-is
    if 'pooler.supabase.com' in (parsed.hostname or ''):
        logger.info("Already using pooler connection")
        return db_url
    
    # Extract project ref from hostname (e.g., db.gxpcrohsbtndndypagie.supabase.co)
    match = re.search(r'db\.([^.]+)\.supabase\.co', parsed.hostname or '')
    if not match:
        # If we can't parse it, try adding IPv4 preference to direct connection
        logger.warning(f"Could not parse Supabase URL, adding IPv4 preference: {parsed.hostname}")
        # Add ?sslmode=require to ensure SSL
        if '?' in db_url:
            db_url += '&'
        else:
            db_url += '?'
        db_url += 'sslmode=require'
        return db_url
    
    project_ref = match.group(1)
    username = parsed.username or 'postgres'
    password = parsed.password or ''
    
    # Try common regions - start with us-east-1, then try others
    regions_to_try = ['us-east-1', 'us-west-1', 'eu-west-1', 'ap-southeast-1']
    region = os.environ.get('SUPABASE_REGION', 'us-east-1')
    
    if region not in regions_to_try:
        regions_to_try.insert(0, region)
    
    # For Vercel serverless: Use transaction pooler (port 6543) with workaround parameter
    # Context7 best practice: Transaction mode for serverless + Vercel workaround
    # Format: postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?workaround=supabase-pooler.vercel
    
    # Update username to include project ref: postgres.[PROJECT-REF]
    pooler_username = f'{username}.{project_ref}' if '.' not in username else username
    
    # Use first region (will try others if connection fails)
    pooler_hostname = f'aws-0-{regions_to_try[0]}.pooler.supabase.com'
    pooler_port = 6543  # Transaction pooler (recommended for serverless/Vercel)
    
    # Rebuild URL with pooler hostname and port
    # No query params needed for psycopg (workaround param is for Vercel Postgres client only)
    pooler_url = urlunparse((
        parsed.scheme,
        f'{pooler_username}:{password}@{pooler_hostname}:{pooler_port}',
        parsed.path,
        parsed.params,
        parsed.query,  # Keep original query params if any
        parsed.fragment
    ))
    
    logger.info(f"Converted to transaction pooler: {pooler_hostname}:{pooler_port} (Vercel workaround)")
    return pooler_url
    
    # Fallback: For direct connections, we need to use IPv4
    # But Vercel can't connect via IPv6, so we must use pooler
    # If pooler conversion failed, return None to indicate we should skip pooler attempt
    logger.warning("Could not determine pooler URL - pooler connection may fail")
    # Return original URL - caller will try direct connection as fallback
    # Note: Direct connection may fail on Vercel due to IPv6
    return db_url


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler for migration."""
    
    def do_POST(self):
        """Handle POST requests for migration."""
        try:
            import psycopg
        except ImportError as e:
            logger.error(f"Failed to import psycopg: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': f'psycopg not available: {str(e)}'
            }).encode())
            return
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body_data = self.rfile.read(content_length)
            body = json.loads(body_data.decode('utf-8'))
            
            sql_content = body.get('sql', '')
            batch_name = body.get('batch_name', 'unknown')
            
            if not sql_content:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'SQL content required'
                }).encode())
                return
            
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'DATABASE_URL not configured'
                }).encode())
                return
            
            logger.info(f"Executing migration batch: {batch_name} ({len(sql_content)} chars)")
            
            # For Vercel serverless: MUST use connection pooler (IPv4 compatible)
            # Context7 best practice: Transaction mode (port 6543) for serverless/Vercel
            # Direct connection uses IPv6 which Vercel doesn't support
            
            # Extract project info and try multiple regions
            import re
            from urllib.parse import urlparse, urlunparse
            
            parsed = urlparse(db_url)
            match = re.search(r'db\.([^.]+)\.supabase\.co', parsed.hostname or '')
            
            if not match:
                # Can't parse - return error
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Could not parse Supabase URL. Ensure DATABASE_URL uses format: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres'
                }).encode())
                return
            
            project_ref = match.group(1)
            username = parsed.username or 'postgres'
            password = parsed.password or ''
            pooler_username = f'{username}.{project_ref}'
            
            # Try all common regions with transaction pooler (port 6543)
            # Context7: Transaction mode is recommended for serverless/Vercel
            # Note: Supabase uses aws-1-{region} format (not aws-0-{region})
            regions = ['us-east-1', 'us-west-1', 'eu-west-1', 'ap-southeast-1', 'ap-northeast-1', 'eu-central-1']
            connection_urls = []
            
            for region in regions:
                # Try aws-1 first (most common), then aws-0 as fallback
                for aws_prefix in ['aws-1', 'aws-0']:
                    pooler_hostname = f'{aws_prefix}-{region}.pooler.supabase.com'
                    pooler_url_try = urlunparse((
                        'postgresql',
                        f'{pooler_username}:{password}@{pooler_hostname}:6543',
                        '/postgres',
                        '',
                        '',
                        ''
                    ))
                    connection_urls.append(pooler_url_try)
            
            logger.info(f"Trying {len(connection_urls)} pooler regions for project {project_ref}")
            
            last_error = None
            for attempt_url in connection_urls:
                try:
                    logger.info(f"Attempting connection: {attempt_url.split('@')[0]}@***")
                    
                    # Execute SQL using psycopg pipeline mode (Context7 best practice)
                    with psycopg.connect(attempt_url, connect_timeout=10) as conn:
                        with conn.pipeline():
                            with conn.cursor() as cur:
                                cur.execute(sql_content)
                            # Pipeline automatically commits on success
                    
                    # Success - break out of retry loop
                    # Estimate rows affected
                    rows_affected = sql_content.count("VALUES") if "VALUES" in sql_content else 0
                    
                    logger.info(f"✅ Successfully executed {batch_name} (estimated {rows_affected} rows)")
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'batch': batch_name,
                        'rows_affected': rows_affected
                    }).encode())
                    return
                    
                except psycopg.Error as e:
                    last_error = e
                    error_msg = f"Connection failed: {type(e).__name__}: {str(e)}"
                    logger.warning(f"❌ {error_msg}")
                    # Try next URL
                    continue
            
            # All connection attempts failed
            if last_error:
                error_msg = f"PostgreSQL error: {type(last_error).__name__}: {str(last_error)}"
                logger.error(f"❌ All connection attempts failed. Last error: {error_msg}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'error': error_msg,
                    'hint': 'Check DATABASE_URL format. For pooler, use: postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres'
                }).encode())
                return
            
        except psycopg.Error as e:
            error_msg = f"PostgreSQL error: {type(e).__name__}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': error_msg
            }).encode())
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': error_msg
            }).encode())
