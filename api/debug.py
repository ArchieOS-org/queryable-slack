"""
Diagnostic endpoint to debug Vercel deployment issues.

DEPLOYMENT INSTRUCTIONS:
1. Copy this file to: /Users/noahdeskin/conductor/queryable-slack-2/frontend/api/debug.py
2. Deploy: cd frontend && vercel --prod --force
3. Access: https://queryable-slack.vercel.app/api/debug
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from pathlib import Path

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Diagnostic endpoint"""
        diagnostics = {}

        # 1. Environment Variables Check
        required_vars = [
            "ANTHROPIC_API_KEY",
            "AI_GATEWAY_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY"
        ]

        env_status = {}
        for var in required_vars:
            value = os.getenv(var, "")
            env_status[var] = {
                "present": bool(value),
                "length": len(value) if value else 0,
                "first_8_chars": value[:8] if value else None
            }

        diagnostics["environment_variables"] = env_status

        # 2. Python Environment
        diagnostics["python"] = {
            "version": sys.version,
            "path": sys.path[:5],  # First 5 paths only
            "cwd": os.getcwd()
        }

        # 3. Module Import Tests
        import_tests = {}

        # Test external package imports
        packages_to_test = [
            "anthropic",
            "openai",
            "supabase",
            "dotenv",
            "pydantic",
            "httpx",
            "websockets"
        ]

        for package in packages_to_test:
            try:
                __import__(package)
                import_tests[package] = "✅ OK"
            except Exception as e:
                import_tests[package] = f"❌ {str(e)}"

        # Test conductor package imports
        try:
            # Add parent directory to path
            current_dir = Path(__file__).parent
            parent_dir = current_dir.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            import conductor
            import_tests["conductor"] = "✅ OK"
        except Exception as e:
            import_tests["conductor"] = f"❌ {str(e)}"

        try:
            from conductor import supabase_query
            import_tests["conductor.supabase_query"] = "✅ OK"
        except Exception as e:
            import_tests["conductor.supabase_query"] = f"❌ {str(e)}"

        try:
            from conductor.supabase_query import query_vector_similarity
            import_tests["query_vector_similarity function"] = "✅ OK"
        except Exception as e:
            import_tests["query_vector_similarity function"] = f"❌ {str(e)}"

        diagnostics["imports"] = import_tests

        # 4. File System Check
        try:
            current_dir = Path(__file__).parent
            parent_dir = current_dir.parent
            conductor_dir = parent_dir / "conductor"

            conductor_files = []
            if conductor_dir.exists():
                conductor_files = [f.name for f in conductor_dir.iterdir() if f.is_file()][:10]

            diagnostics["filesystem"] = {
                "api_dir": str(current_dir),
                "parent_dir": str(parent_dir),
                "conductor_dir_exists": conductor_dir.exists(),
                "conductor_dir_path": str(conductor_dir),
                "conductor_files_sample": conductor_files
            }
        except Exception as e:
            diagnostics["filesystem"] = {"error": str(e)}

        # 5. Vercel Environment Detection
        diagnostics["vercel"] = {
            "is_vercel": bool(os.getenv("VERCEL")),
            "vercel_env": os.getenv("VERCEL_ENV"),
            "vercel_region": os.getenv("VERCEL_REGION"),
            "vercel_url": os.getenv("VERCEL_URL")
        }

        # 6. Diagnosis Summary
        issues_found = []

        if not env_status["ANTHROPIC_API_KEY"]["present"]:
            issues_found.append("❌ CRITICAL: ANTHROPIC_API_KEY not set")
        if not env_status["AI_GATEWAY_API_KEY"]["present"]:
            issues_found.append("❌ CRITICAL: AI_GATEWAY_API_KEY not set")
        if not env_status["SUPABASE_URL"]["present"]:
            issues_found.append("❌ CRITICAL: SUPABASE_URL not set")
        if not env_status["SUPABASE_ANON_KEY"]["present"]:
            issues_found.append("❌ CRITICAL: SUPABASE_ANON_KEY not set")

        for package, status in import_tests.items():
            if "❌" in status:
                issues_found.append(f"❌ Import failed: {package}")

        diagnostics["summary"] = {
            "total_issues": len(issues_found),
            "issues": issues_found if issues_found else ["✅ All checks passed!"],
            "status": "HEALTHY" if not issues_found else "UNHEALTHY",
            "next_steps": self._get_next_steps(issues_found)
        }

        # Return JSON response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(diagnostics, indent=2).encode())

    def _get_next_steps(self, issues):
        """Provide actionable next steps based on issues found"""
        if not issues:
            return ["System is healthy. You can proceed with testing /api/query endpoint."]

        steps = []

        has_env_issues = any("ANTHROPIC_API_KEY" in issue or "AI_GATEWAY" in issue or "SUPABASE" in issue for issue in issues)
        has_import_issues = any("Import failed" in issue for issue in issues)

        if has_env_issues:
            steps.append("1. Add missing environment variables:")
            steps.append("   vercel env add ANTHROPIC_API_KEY production")
            steps.append("   vercel env add AI_GATEWAY_API_KEY production")
            steps.append("2. Redeploy: vercel --prod --force")

        if has_import_issues:
            steps.append("1. Check requirements.txt includes all dependencies")
            steps.append("2. For 'supabase' import errors, add sub-dependencies:")
            steps.append("   httpx, postgrest-py, storage3, gotrue, realtime-py")
            steps.append("3. Redeploy: vercel --prod --force")

        if not steps:
            steps.append("Check Vercel deployment logs: vercel logs --follow")

        return steps

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
