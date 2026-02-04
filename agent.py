#!/usr/bin/env python3
"""
Browser Challenge Agent
Solves 30 browser challenges using Gemini Flash + Playwright
"""

import asyncio
import base64
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import async_playwright, Page
import google.generativeai as genai

# ============ CONFIG ============
CHALLENGE_URL = "https://serene-frangipane-7fd25b.netlify.app/"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")  # Gemini 3 Flash Preview - best for agentic
MAX_RETRIES_PER_CHALLENGE = 3
SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

@dataclass
class Stats:
    """Track metrics for the run"""
    start_time: float = 0
    end_time: float = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    challenges_solved: int = 0
    challenges_failed: int = 0
    actions_taken: int = 0
    errors: list = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def cost_estimate(self) -> float:
        # Gemini Flash pricing (approximate)
        # Input: $0.075 / 1M tokens, Output: $0.30 / 1M tokens
        input_cost = (self.input_tokens / 1_000_000) * 0.075
        output_cost = (self.output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost
    
    def to_dict(self) -> dict:
        return {
            "duration_seconds": round(self.duration_seconds, 2),
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_estimate_usd": round(self.cost_estimate, 4),
            "challenges_solved": self.challenges_solved,
            "challenges_failed": self.challenges_failed,
            "actions_taken": self.actions_taken,
            "errors": self.errors[-10:],  # Last 10 errors
        }

stats = Stats()

# ============ GEMINI SETUP ============
def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)

SYSTEM_PROMPT = """You are a browser automation agent. Analyze screenshots and determine the next action to solve UI challenges.

RESPONSE FORMAT (JSON only):
{
  "thinking": "brief analysis of what you see",
  "action": "click|type|select|scroll|press|wait|done",
  "target": "CSS selector or description",
  "value": "text to type or key to press (if applicable)",
  "confidence": 0.0-1.0
}

ACTIONS:
- click: Click an element. target = CSS selector like "button.submit" or "#login"
- type: Type text into focused element or specified input. target = selector, value = text
- select: Select dropdown option. target = selector, value = option text
- scroll: Scroll the page. target = "up"|"down"|"element-selector"
- press: Press a key. value = "Enter"|"Tab"|"Escape"|etc
- wait: Wait for something. value = milliseconds
- done: Challenge appears complete, move to next

TIPS:
- Look for buttons, inputs, checkboxes, links
- Read any instructions on screen
- If stuck, try clicking the most prominent interactive element
- Watch for success messages or visual changes indicating completion
"""

async def analyze_screenshot(model, screenshot_bytes: bytes, challenge_num: int) -> dict:
    """Send screenshot to Gemini and get action"""
    global stats
    
    # Save screenshot for debugging
    screenshot_path = SCREENSHOT_DIR / f"challenge_{challenge_num}_{int(time.time())}.png"
    screenshot_path.write_bytes(screenshot_bytes)
    
    # Create image part
    image_part = {
        "mime_type": "image/png",
        "data": base64.b64encode(screenshot_bytes).decode()
    }
    
    prompt = f"Challenge #{challenge_num}. What action should I take? Respond with JSON only."
    
    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, image_part, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Track tokens
        if hasattr(response, 'usage_metadata'):
            stats.input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
            stats.output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
            stats.total_tokens = stats.input_tokens + stats.output_tokens
        
        # Parse response
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text)
    except Exception as e:
        stats.errors.append(f"Gemini error: {str(e)}")
        return {"action": "wait", "value": "500", "thinking": f"Error: {e}"}

# ============ BROWSER ACTIONS ============
async def execute_action(page: Page, action: dict) -> bool:
    """Execute the action from Gemini"""
    global stats
    stats.actions_taken += 1
    
    action_type = action.get("action", "wait")
    target = action.get("target", "")
    value = action.get("value", "")
    
    print(f"  → {action_type}: {target} {value}")
    
    try:
        if action_type == "click":
            if target:
                await page.click(target, timeout=3000)
            else:
                # Click center of page as fallback
                await page.mouse.click(640, 360)
                
        elif action_type == "type":
            if target:
                await page.fill(target, value)
            else:
                await page.keyboard.type(value)
                
        elif action_type == "select":
            await page.select_option(target, label=value)
            
        elif action_type == "scroll":
            if target == "down":
                await page.mouse.wheel(0, 300)
            elif target == "up":
                await page.mouse.wheel(0, -300)
            else:
                elem = await page.query_selector(target)
                if elem:
                    await elem.scroll_into_view_if_needed()
                    
        elif action_type == "press":
            await page.keyboard.press(value)
            
        elif action_type == "wait":
            await asyncio.sleep(int(value or 500) / 1000)
            
        elif action_type == "done":
            return True  # Signal challenge complete
            
        # Small delay after action
        await asyncio.sleep(0.2)
        return False
        
    except Exception as e:
        stats.errors.append(f"Action error ({action_type}): {str(e)}")
        print(f"  ⚠ Action failed: {e}")
        await asyncio.sleep(0.3)
        return False

async def detect_challenge_change(page: Page, prev_url: str, prev_content: str) -> bool:
    """Detect if we moved to a new challenge"""
    try:
        current_url = page.url
        if current_url != prev_url:
            return True
        
        # Check for content changes suggesting new challenge
        body = await page.query_selector("body")
        if body:
            content = await body.inner_text()
            # Significant content change might indicate new challenge
            if len(content) > 0 and content != prev_content:
                # Look for challenge indicators
                if any(x in content.lower() for x in ["challenge", "level", "task", "complete", "success", "next"]):
                    return True
        return False
    except:
        return False

# ============ MAIN SOLVER ============
async def solve_challenge(page: Page, model, challenge_num: int) -> bool:
    """Solve a single challenge"""
    print(f"\n{'='*50}")
    print(f"🎯 Challenge #{challenge_num}")
    print(f"{'='*50}")
    
    prev_url = page.url
    prev_content = ""
    
    for attempt in range(MAX_RETRIES_PER_CHALLENGE * 5):  # More attempts per challenge
        # Take screenshot
        screenshot = await page.screenshot()
        
        # Get action from Gemini
        action = await analyze_screenshot(model, screenshot, challenge_num)
        print(f"  💭 {action.get('thinking', 'No analysis')[:80]}")
        
        # Execute action
        is_done = await execute_action(page, action)
        
        if is_done or action.get("action") == "done":
            print(f"  ✅ Challenge #{challenge_num} marked complete")
            stats.challenges_solved += 1
            return True
        
        # Check if challenge changed
        if await detect_challenge_change(page, prev_url, prev_content):
            print(f"  ✅ Challenge #{challenge_num} complete (page changed)")
            stats.challenges_solved += 1
            return True
        
        # Update tracking
        try:
            body = await page.query_selector("body")
            if body:
                prev_content = await body.inner_text()
        except:
            pass
        prev_url = page.url
        
        # Timeout check
        if time.time() - stats.start_time > 290:  # 4:50 - leave buffer
            print("  ⚠ Approaching time limit!")
            break
    
    print(f"  ❌ Challenge #{challenge_num} failed (max attempts)")
    stats.challenges_failed += 1
    return False

async def run_agent():
    """Main agent loop"""
    global stats
    
    print("🤖 Browser Challenge Agent")
    print(f"📍 Target: {CHALLENGE_URL}")
    print(f"🧠 Model: {GEMINI_MODEL}")
    print("="*50)
    
    # Setup Gemini
    model = setup_gemini()
    print("✅ Gemini initialized")
    
    stats.start_time = time.time()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        print(f"✅ Browser launched")
        
        # Navigate to challenge
        await page.goto(CHALLENGE_URL, wait_until="networkidle")
        print(f"✅ Loaded challenge page")
        await asyncio.sleep(1)
        
        # Solve challenges
        for i in range(1, 31):
            if time.time() - stats.start_time > 290:
                print("\n⏰ Time limit approaching, stopping...")
                break
                
            success = await solve_challenge(page, model, i)
            
            if not success:
                # Try to find and click "next" or "skip" button
                try:
                    next_btn = await page.query_selector("text=Next, text=Skip, text=Continue, button")
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(0.5)
                except:
                    pass
        
        await browser.close()
    
    stats.end_time = time.time()
    
    # Print results
    print("\n" + "="*50)
    print("📊 RESULTS")
    print("="*50)
    results = stats.to_dict()
    print(json.dumps(results, indent=2))
    
    # Save results
    results_path = Path("run_results.json")
    results_path.write_text(json.dumps(results, indent=2))
    print(f"\n💾 Results saved to {results_path}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_agent())
