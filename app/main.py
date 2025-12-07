from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import language_tool_python
import os
import asyncio
import shutil
import glob
import requests

app = FastAPI(title="LanguageTool Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CheckRequest(BaseModel):
    """Request model for JSON grammar check endpoint"""
    text: str
    language: Optional[str] = "en-US"
    questionText: Optional[str] = None

# Initialize LanguageTool (only self-hosted mode is supported)
LANGTOOL_SERVER = os.getenv("LANGTOOL_SERVER", "http://localhost:8011")  # Java server port
LANGTOOL_AVAILABLE = False
tool = None
INIT_ERROR = None


def clear_languagetool_cache():
    """Clear corrupted LanguageTool cache files"""
    try:
        # Get the default cache path
        cache_path = os.path.join(os.path.expanduser("~"), ".cache", "language_tool_python")
        if os.path.exists(cache_path):
            print(f"Clearing LanguageTool cache at: {cache_path}")
            # Remove zip files that might be corrupted
            zip_files = glob.glob(os.path.join(cache_path, "*.zip"))
            for zip_file in zip_files:
                try:
                    os.remove(zip_file)
                    print(f"  Removed: {zip_file}")
                except Exception as e:
                    print(f"  Failed to remove {zip_file}: {e}")
            
            # Remove LanguageTool directories to force re-download
            lt_dirs = glob.glob(os.path.join(cache_path, "LanguageTool*"))
            for lt_dir in lt_dirs:
                if os.path.isdir(lt_dir):
                    try:
                        shutil.rmtree(lt_dir)
                        print(f"  Removed directory: {lt_dir}")
                    except Exception as e:
                        print(f"  Failed to remove {lt_dir}: {e}")
            return True
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return False
    return False


def initialize_languagetool():
    """Initialize LanguageTool with retry logic"""
    global tool, LANGTOOL_AVAILABLE, INIT_ERROR
    
    if not LANGTOOL_SERVER:
        INIT_ERROR = "LANGTOOL_SERVER is not configured. Please set the Java server URL."
        print(f"✗ {INIT_ERROR}")
        return False
    
    print(f"Initializing LanguageTool with remote server: {LANGTOOL_SERVER}")
    try:
        tool = language_tool_python.LanguageTool(
            language="en-US",
            remote_server=LANGTOOL_SERVER
        )
        LANGTOOL_AVAILABLE = True
        print("✓ LanguageTool remote server initialized successfully")
        return True
    except Exception as e:
        INIT_ERROR = str(e)
        print(f"✗ Failed to connect to remote server: {e}")
        print(f"  Server URL: {LANGTOOL_SERVER}")
        print("  Make sure Java server is running: java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public")
        return False


# Try to initialize LanguageTool
try:
    if not initialize_languagetool():
        print("Falling back to basic mode")
        LANGTOOL_AVAILABLE = False
        tool = None
except Exception as e:
    INIT_ERROR = str(e)
    print(f"✗ Unexpected error during initialization: {e}")
    import traceback
    print(f"  Traceback: {traceback.format_exc()}")
    print("Falling back to basic mode")
    LANGTOOL_AVAILABLE = False
    tool = None


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "languagetool",
        "version": "1.0.0",
        "available": LANGTOOL_AVAILABLE,
        "server": LANGTOOL_SERVER,
        "error": INIT_ERROR if not LANGTOOL_AVAILABLE else None
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy" if LANGTOOL_AVAILABLE else "degraded",
        "service": "languagetool",
        "version": "1.0.0",
        "available": LANGTOOL_AVAILABLE
    }


@app.get("/info")
async def info():
    """Get service information"""
    return {
        "service": "LanguageTool Grammar Check Service",
        "version": "1.0.0",
        "description": "Grammar and spell checking using LanguageTool",
        "available": LANGTOOL_AVAILABLE,
        "server": LANGTOOL_SERVER,
        "mode": "self_hosted_server",
        "initialization_error": INIT_ERROR if not LANGTOOL_AVAILABLE else None,
        "endpoints": {
            "health": "GET /health",
            "info": "GET /info",
            "test_connection": "GET /test-connection (test connection to Java server)",
            "check": "POST /v2/check (check grammar and spelling)",
            "check_json": "POST /v2/check/json (JSON body format)",
            "reinit": "POST /reinit (clear cache and reinitialize)"
        },
        "supported_languages": ["en-US", "en-GB", "en-AU", "en-NZ", "en-ZA", "en-CA"],
        "note": "Service requires a running LanguageTool Java server (default http://localhost:8011).",
        "configuration": {
            "LANGTOOL_SERVER": "URL of your LanguageTool Java server (e.g., http://localhost:8011). Python service runs on 8010, Java server should use 8011 to avoid port conflict."
        },
        "troubleshooting": {
            "if_not_available": "Check console logs for initialization error. Common issues: Java server not running or incorrect LANGTOOL_SERVER value.",
            "check_java": "Run 'java -version' to verify Java is installed",
            "check_logs": "Look for 'Failed to connect to remote server' in service startup logs",
            "clear_cache": "If you see 'File is not a zip file' error, try POST /reinit to clear cache and reinitialize"
        }
    }


@app.get("/test-connection")
async def test_connection():
    """Test connection to LanguageTool server"""
    
    if not LANGTOOL_SERVER:
        return {
            "connected": False,
            "message": "LANGTOOL_SERVER environment variable is not set",
            "server": None,
            "suggestion": "Set LANGTOOL_SERVER=http://localhost:8011 and restart the service"
        }
    
    try:
        # Test connection to Java server
        test_url = f"{LANGTOOL_SERVER}/v2/languages"
        response = requests.get(test_url, timeout=5)
        
        if response.status_code == 200:
            return {
                "connected": True,
                "message": "Successfully connected to LanguageTool server",
                "server": LANGTOOL_SERVER,
                "status": "ok"
            }
        else:
            return {
                "connected": False,
                "message": f"Server returned status code {response.status_code}",
                "server": LANGTOOL_SERVER,
                "status_code": response.status_code
            }
    except requests.exceptions.ConnectionError:
        return {
            "connected": False,
            "message": f"Cannot connect to LanguageTool server at {LANGTOOL_SERVER}",
            "server": LANGTOOL_SERVER,
            "error": "Connection refused",
            "suggestion": "Make sure Java server is running: java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8011 --public"
        }
    except requests.exceptions.Timeout:
        return {
            "connected": False,
            "message": f"Connection timeout to {LANGTOOL_SERVER}",
            "server": LANGTOOL_SERVER,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Error testing connection: {str(e)}",
            "server": LANGTOOL_SERVER,
            "error": str(e)
        }


@app.post("/reinit")
async def reinit():
    """Clear LanguageTool cache and reinitialize"""
    global tool, LANGTOOL_AVAILABLE, INIT_ERROR
    
    try:
        print("Manual reinitialization requested...")
        
        # Clear cache
        cache_cleared = clear_languagetool_cache()
        
        # Reset state
        tool = None
        LANGTOOL_AVAILABLE = False
        INIT_ERROR = None
        
        # Try to reinitialize
        success = initialize_languagetool()
        
        return {
            "success": success,
            "available": LANGTOOL_AVAILABLE,
            "cache_cleared": cache_cleared,
            "error": INIT_ERROR if not success else None,
            "message": "LanguageTool reinitialized successfully" if success else f"Reinitialization failed: {INIT_ERROR}",
            "server": LANGTOOL_SERVER,
            "suggestion": "Ensure Java server is running on port 8011"
        }
    except Exception as e:
        import traceback
        error_msg = f"Error during reinitialization: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {
            "success": False,
            "available": False,
            "cache_cleared": False,
            "error": error_msg,
            "message": "Reinitialization failed with exception"
        }


async def check_grammar_internal(text: str, language: str = "en-US", question_text: Optional[str] = None):
    """
    Internal function to check grammar and spelling
    
    Args:
        text: Text to check
        language: Language code
        question_text: Optional question text for context
    
    Returns the result dictionary
    """
    if not LANGTOOL_AVAILABLE or not tool:
        # Fallback to basic mock response
        result = {
            "language": {"name": "English", "code": language},
            "matches": [
                {
                    "message": "LanguageTool is not available. Please check server configuration.",
                    "shortMessage": "Service unavailable",
                    "replacements": [],
                    "offset": 0,
                    "length": len(text),
                    "rule": {"id": "SERVICE_UNAVAILABLE", "description": "LanguageTool service not available"},
                }
            ],
        }
        # Add questionText to response if provided
        if question_text:
            result["questionText"] = question_text
        return result
    
    try:
        # Check text with LanguageTool - run in thread pool to avoid blocking
        # tool.check() is a blocking I/O operation
        matches = await asyncio.to_thread(tool.check, text)
        
        # Convert LanguageTool matches to API format
        result_matches = []
        for match in matches:
            result_matches.append({
                "message": match.message,
                "shortMessage": match.message[:50] if match.message else "",
                "replacements": [{"value": repl} for repl in (match.replacements or [])],
                "offset": match.offset,
                "length": match.errorLength,
                "rule": {
                    "id": match.ruleId or "UNKNOWN",
                    "description": match.message or "Grammar issue"
                },
                "context": {
                    "text": match.context or text[match.offset:match.offset + match.errorLength],
                    "offset": match.offset,
                    "length": match.errorLength
                }
            })
        
        # Determine language name
        lang_names = {
            "en-US": "English (US)",
            "en-GB": "English (UK)",
            "en-AU": "English (Australia)",
            "en-NZ": "English (New Zealand)",
            "en-ZA": "English (South Africa)",
            "en-CA": "English (Canada)"
        }
        
        result = {
            "language": {
                "name": lang_names.get(language, "English"),
                "code": language
            },
            "matches": result_matches
        }
        
        # Add questionText to response if provided
        if question_text:
            result["questionText"] = question_text
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking grammar: {str(e)}"
        )


@app.post("/v2/check")
async def check(
    text: str = Form(...), 
    language: str = Form("en-US"),
    questionText: Optional[str] = Form(None)
):
    """
    Check grammar and spelling using LanguageTool (form-data format)
    
    - **text**: Text to check
    - **language**: Language code (default: en-US)
    - **questionText**: Optional question text for context
    """
    return await check_grammar_internal(text, language, questionText)


@app.post("/v2/check/json")
async def check_json(request: CheckRequest):
    """
    Check grammar and spelling using LanguageTool (JSON body format)
    
    **Request body:**
    ```json
    {
        "text": "Text to check for grammar and spelling errors",
        "language": "en-US",
        "questionText": "Optional question text for context"
    }
    ```
    
    **Response:**
    ```json
    {
        "language": {
            "name": "English (US)",
            "code": "en-US"
        },
        "questionText": "Optional question text (if provided in request)",
        "matches": [
            {
                "message": "Possible spelling mistake",
                "shortMessage": "Spelling",
                "replacements": [{"value": "correct"}],
                "offset": 0,
                "length": 5,
                "rule": {
                    "id": "MORFOLOGIK_RULE_EN_US",
                    "description": "Possible spelling mistake"
                },
                "context": {
                    "text": "...",
                    "offset": 0,
                    "length": 5
                }
            }
        ]
    }
    ```
    """
    return await check_grammar_internal(
        request.text, 
        request.language or "en-US",
        request.questionText
    )

