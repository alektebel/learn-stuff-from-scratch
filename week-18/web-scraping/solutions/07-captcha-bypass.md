# CAPTCHA Bypass - Understanding and Techniques

## ⚠️ Legal and Ethical Warning

**READ THIS FIRST:**

CAPTCHA bypass techniques exist in a legal and ethical gray area. This guide is for **educational purposes** to understand how anti-bot systems work and how they can be circumvented. 

**You should NOT:**
- Bypass CAPTCHAs on sites that explicitly prohibit automation
- Violate Terms of Service agreements
- Access systems without authorization
- Use these techniques for malicious purposes

**Legal consequences** can include:
- Civil lawsuits (breach of contract, trespass to chattels)
- Criminal charges (Computer Fraud and Abuse Act in US, similar laws globally)
- Permanent IP bans
- Cease and desist orders

**Always:**
- Get explicit permission before scraping
- Use official APIs when available
- Respect rate limits even if you can bypass protections
- Consider the intent behind the CAPTCHA (security vs. business model)

## What is CAPTCHA?

**CAPTCHA** = Completely Automated Public Turing test to tell Computers and Humans Apart

**Purpose:**
- Prevent automated bot access
- Protect against spam
- Prevent scraping/crawling
- Rate limiting
- Protect login forms
- Prevent ticket scalping

## Evolution of CAPTCHA

### Generation 1: Text CAPTCHAs (1997-2010)

**Technique:** Distorted text images

```
┌─────────────────────┐
│  ╔═╗ ╦ ╦ ╔═╗ ╔═╗  │
│  ╠═╝ ║║║ ║   ╚═╗  │
│  ╩   ╚╩╝ ╚═╝ ╚═╝  │
└─────────────────────┘
"Enter the text above: ____"
```

**How it works:**
1. Generate random text
2. Apply distortions (rotation, skew, noise)
3. Render as image
4. Ask user to type text

**Bypass methods:**
- **OCR (Optical Character Recognition)**
  - Tesseract OCR
  - Pre-processing (denoising, deskewing)
  - Character segmentation
  - Machine learning classifiers

- **Pattern recognition**
  - Train CNN on CAPTCHA dataset
  - High accuracy (>90%) with enough training data

**Why it failed:**
- ML models became too good
- Poor user experience
- Accessibility issues (blind users)

### Generation 2: Audio CAPTCHAs (2006-2015)

**Technique:** Distorted spoken text/numbers

**How it works:**
1. Generate random text
2. Text-to-speech synthesis
3. Add noise, distortion, background sounds
4. User types what they hear

**Bypass methods:**
- Speech recognition (Google Speech API, Whisper)
- Audio preprocessing (noise reduction, normalization)
- Often easier than visual CAPTCHAs

**Why it failed:**
- Modern speech recognition is very accurate
- Poor user experience
- Still accessibility issues

### Generation 3: reCAPTCHA v1 (2007-2013)

**Technique:** Digitized book text

**How it works:**
1. Two words: one known, one unknown (from book scanning)
2. User must type both
3. Known word validates user
4. Unknown word helps digitize books

**Bypass methods:**
- Similar to text CAPTCHAs (OCR)
- Only need to solve the known word correctly
- Can send unknown word to human solver services

**Innovation:** Useful work (book digitization)

### Generation 4: reCAPTCHA v2 (2014-present)

**Technique:** "I'm not a robot" checkbox + image challenges

```
┌──────────────────────────────────┐
│  ☐ I'm not a robot              │
│       reCAPTCHA                  │
└──────────────────────────────────┘

If suspicious:
┌──────────────────────────────────┐
│ Select all images with traffic   │
│ lights                           │
│ ┌───┬───┬───┬───┐               │
│ │ 1 │ 2 │ 3 │ 4 │               │
│ ├───┼───┼───┼───┤               │
│ │ 5 │ 6 │ 7 │ 8 │               │
│ ├───┼───┼───┼───┤               │
│ │ 9 │10 │11 │12 │               │
│ └───┴───┴───┴───┘               │
│         [VERIFY]                 │
└──────────────────────────────────┘
```

**How it works:**
1. User clicks checkbox
2. JavaScript analyzes:
   - Mouse movement patterns
   - Browser fingerprint
   - Cookies from previous browsing
   - IP reputation
3. If score is high → Pass immediately
4. If score is low → Show image challenge

**What reCAPTCHA v2 analyzes:**

```python
# Behavioral Signals (pseudocode)
signals = {
    # Mouse behavior
    'mouse_movements': analyze_trajectory(),
    'click_duration': measure_click_time(),
    'mouse_acceleration': detect_human_curves(),
    
    # Browser fingerprint
    'user_agent': get_browser_info(),
    'screen_resolution': window.screen,
    'timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
    'language': navigator.language,
    'plugins': navigator.plugins,
    'canvas_fingerprint': generate_canvas_hash(),
    'webgl_fingerprint': get_webgl_info(),
    'fonts': detect_installed_fonts(),
    
    # Behavioral
    'cookies': check_recaptcha_cookies(),
    'browsing_history': check_google_cookies(),
    'typing_patterns': analyze_keyboard_timing(),
    
    # Network
    'ip_reputation': lookup_ip_score(),
    'datacenter_ip': is_datacenter_ip(),
    'vpn_detection': detect_vpn(),
    
    # Prior interactions
    'recaptcha_score': get_previous_scores(),
    'google_account': is_logged_in_to_google(),
}

risk_score = ml_model.predict(signals)

if risk_score < threshold:
    return "pass"
else:
    return "show_image_challenge"
```

**Image Challenge Types:**
- Select all traffic lights
- Select all crosswalks
- Select all buses
- Select all bicycles
- Select all stairs

**Bypass methods:**

**1. Behavioral Mimicry**
```python
# Simulate human mouse movement
def human_mouse_move(start, end, duration=1.0):
    """
    Move mouse with human-like bezier curve
    """
    # Generate Bezier curve points
    points = bezier_curve(start, end, control_points=2)
    
    # Add randomness
    points = add_jitter(points, amount=5)
    
    # Vary speed (fast in middle, slow at ends)
    timestamps = ease_in_out_timing(len(points), duration)
    
    for point, timestamp in zip(points, timestamps):
        move_mouse(point)
        time.sleep(timestamp)

# Use real browser with Selenium/Playwright
from selenium import webdriver
from selenium_stealth import stealth

driver = webdriver.Chrome()
stealth(driver,
    languages=["en-US", "en"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris OpenGL Engine",
    fix_hairline=True,
)
```

**2. Browser Fingerprint Manipulation**
```python
# Modify Playwright to look more human
async def create_stealthy_browser():
    browser = await playwright.chromium.launch(
        headless=False,  # Headless is often detected
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        locale='en-US',
        timezone_id='America/New_York',
        permissions=['geolocation'],
    )
    
    # Remove webdriver property
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return browser, context
```

**3. Image Challenge Solving with ML**

```python
import torch
from torchvision import models, transforms
from PIL import Image

class RecaptchaImageSolver:
    """
    Solve reCAPTCHA image challenges using CNN
    """
    def __init__(self):
        # Use pre-trained model fine-tuned on CAPTCHA images
        self.model = models.resnet50(pretrained=True)
        self.model.fc = torch.nn.Linear(2048, 100)  # 100 object classes
        self.model.load_state_dict(torch.load('recaptcha_model.pth'))
        self.model.eval()
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])
    
    def solve_challenge(self, images, target_class):
        """
        Identify which images contain target_class
        
        images: list of PIL Images (9-16 tiles)
        target_class: str like "traffic light", "crosswalk", etc.
        
        Returns: list of indices containing target
        """
        results = []
        
        for idx, img in enumerate(images):
            # Preprocess image
            img_tensor = self.transform(img).unsqueeze(0)
            
            # Predict
            with torch.no_grad():
                output = self.model(img_tensor)
                probabilities = torch.nn.functional.softmax(output, dim=1)
            
            # Check if target class is present
            target_idx = self.class_to_idx[target_class]
            if probabilities[0, target_idx] > 0.7:  # Confidence threshold
                results.append(idx)
        
        return results

# Usage
solver = RecaptchaImageSolver()

# Extract images from reCAPTCHA grid
tiles = extract_image_tiles(recaptcha_iframe)

# Solve: "Select all traffic lights"
selected = solver.solve_challenge(tiles, "traffic_light")

# Click selected tiles
for idx in selected:
    click_tile(idx)
```

**4. Using CAPTCHA Solving Services**

```python
import requests

class TwoCaptchaSolver:
    """
    Use 2Captcha service (human workers)
    Cost: ~$2.99 per 1000 CAPTCHAs
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"
    
    def solve_recaptcha(self, site_key, page_url):
        """
        Solve reCAPTCHA v2
        
        site_key: data-sitekey attribute from page
        page_url: URL where CAPTCHA appears
        """
        # Submit CAPTCHA
        submit_response = requests.get(
            f"{self.base_url}/in.php",
            params={
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1
            }
        )
        
        result = submit_response.json()
        captcha_id = result['request']
        
        # Poll for result (usually 10-30 seconds)
        for _ in range(60):  # Max 60 attempts
            time.sleep(5)
            
            result_response = requests.get(
                f"{self.base_url}/res.php",
                params={
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }
            )
            
            result = result_response.json()
            if result['status'] == 1:
                return result['request']  # g-recaptcha-response token
        
        raise Exception("CAPTCHA solving timeout")

# Usage
solver = TwoCaptchaSolver(api_key='your_api_key')
token = solver.solve_recaptcha(
    site_key='6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-',
    page_url='https://example.com/page'
)

# Submit token in form
submit_form(recaptcha_response=token)
```

**Why v2 is harder:**
- Behavioral analysis
- Requires real browser
- Image challenges require vision
- Google's vast data on users

### Generation 5: reCAPTCHA v3 (2018-present)

**Technique:** Invisible, score-based

**How it works:**
1. No user interaction
2. JavaScript runs in background
3. Analyzes behavior across entire site
4. Returns risk score (0.0 to 1.0)
5. Site decides what to do with score

```javascript
// Frontend integration
grecaptcha.ready(function() {
    grecaptcha.execute('site_key', {action: 'submit'})
        .then(function(token) {
            // Send token to backend
            fetch('/verify', {
                method: 'POST',
                body: JSON.stringify({token: token})
            });
        });
});

// Backend verification
const response = await fetch(
    `https://www.google.com/recaptcha/api/siteverify`,
    {
        method: 'POST',
        body: `secret=${secret_key}&response=${token}`
    }
);

const result = await response.json();
// Example response:
// {
//     "success": true,
//     "score": 0.7,  // 0.0 = bot, 1.0 = human
//     "action": "submit",
//     "challenge_ts": "2024-01-01T00:00:00Z",
//     "hostname": "example.com"
// }

// Site decides
if (result.score < 0.5) {
    return "rejected";  // Likely bot
} else if (result.score < 0.7) {
    return "show_captcha";  // Unsure, show v2
} else {
    return "approved";  // Likely human
}
```

**What v3 analyzes:**
- Everything from v2, plus:
- Time spent on page
- Scroll behavior
- Form filling patterns
- Navigation patterns
- Cross-site behavior (Google ecosystem)

**Bypass methods:**

**1. Use Real Browsers with Automation**
```python
# Playwright with stealth plugins
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def create_human_like_browser():
    async with async_playwright() as p:
        # Use real Chrome (not Chromium)
        browser = await p.chromium.launch(
            channel='chrome',
            headless=False,  # Must be headed for best scores
            slow_mo=50,  # Slow down actions
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0...',
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        # Apply stealth patches
        await stealth_async(context)
        
        page = await context.new_page()
        
        # Simulate human behavior before form
        await page.goto('https://example.com')
        await asyncio.sleep(2 + random.random() * 3)
        
        # Random scrolling
        await human_like_scroll(page)
        
        # Mouse movements
        await random_mouse_movements(page)
        
        # Then interact with form
        await page.fill('#email', 'user@example.com', delay=100)  # Type slowly
        
        return page
```

**2. Collect Tokens from Real Users**
```python
# Controversial: Use real user tokens
# Some sites collect tokens from legitimate users
# And reuse them for bot requests
# This is essentially a Man-in-the-Middle attack

def harvest_tokens():
    """
    DON'T DO THIS - ILLEGAL AND UNETHICAL
    Just showing it exists
    """
    # Set up proxy
    # Intercept legitimate user requests
    # Extract reCAPTCHA tokens
    # Store in database
    # Reuse within 2-minute validity window
    pass
```

**3. Token Recycling** (doesn't work well)
- Tokens are short-lived (2 minutes)
- Tied to user session
- Limited reuse potential

**Why v3 is hardest:**
- Invisible = can't be detected easily
- Behavioral scoring across entire session
- Leverages Google's vast user data
- Adaptive (learns from bypass attempts)

### Other CAPTCHA Systems

#### hCaptcha (2017-present)

**Similar to reCAPTCHA v2** but:
- Privacy-focused (doesn't sell data to Google)
- Pays website owners
- Uses same image challenge format

**Bypass:** Same techniques as reCAPTCHA v2

#### FunCaptcha (Arkose Labs)

**Technique:** Interactive games

```
┌─────────────────────────────┐
│ Roll the ball to upright    │
│ position                    │
│                             │
│      🎯                     │
│                             │
│   ◄━━━━━━━━━━━►           │
└─────────────────────────────┘
```

**Types:**
- Roll dice to match number
- Rotate image to correct orientation
- Select images in order
- Drag and drop puzzles

**Bypass:**
- Hardest to automate (interactive)
- Each challenge type needs custom solver
- ML models for image orientation
- Physics simulation for rolling

#### GeeTest

**Technique:** Sliding puzzle

```
┌─────────────────────────────┐
│ Slide to complete the       │
│ puzzle                      │
│                             │
│  [  ]-----------------►     │
│                             │
│  [🧩]  ← missing piece     │
└─────────────────────────────┘
```

**How it works:**
1. Show image with missing piece
2. User drags slider to position piece
3. Analyzes drag trajectory and speed

**Bypass:**
- Computer vision to find puzzle position
- Simulate human drag pattern
- Add noise to trajectory

## Bypass Success Rates (2024)

| CAPTCHA Type | Automated | ML-Based | Human Service |
|--------------|-----------|----------|---------------|
| Text v1      | 95%+      | 98%+     | 99%+          |
| Audio        | 85%+      | 90%+     | 99%+          |
| reCAPTCHA v2 | 30%       | 70%      | 95%+          |
| reCAPTCHA v3 | 10%       | 40%      | N/A (invisible) |
| hCaptcha     | 25%       | 65%      | 95%+          |
| FunCaptcha   | 5%        | 30%      | 90%+          |

**Note:** Success rates vary by implementation quality

## The Arms Race

### CAPTCHA Evolution
1. Humans beat text CAPTCHAs → Image CAPTCHAs
2. ML beats image classification → Behavioral analysis
3. Bots mimic behavior → Multi-factor analysis
4. Bots use real browsers → Ecosystem analysis

### Current State (2024)
- reCAPTCHA v3 is most sophisticated
- Analyzes user across Google ecosystem
- No single bypass works consistently
- Cat-and-mouse game continues

### Future Trends
- **Biometric verification** (Face ID, fingerprint)
- **Device attestation** (Apple/Android platform verification)
- **Web3 solutions** (Proof of Humanity via blockchain)
- **Economic CAPTCHAs** (small payments)
- **Federated learning** (privacy-preserving ML)

## Practical Advice

### When You Encounter CAPTCHA

**1. Try the Official API First**
- Many sites have APIs that don't require CAPTCHA
- Even if limited, often sufficient
- Legal and ethical

**2. Request Permission**
- Contact website owner
- Explain your use case
- Get written permission
- May get API access or CAPTCHA exemption

**3. Use CAPTCHA Solving Services**
- 2Captcha, Anti-Captcha, DeathByCaptcha
- Costs $2-5 per 1000 solves
- Uses human workers
- Legal gray area but widely used

**4. Respect Rate Limits**
- Even if you bypass, don't overwhelm server
- Implement delays
- Follow robots.txt

**5. Build Relationships**
- Identify yourself in User-Agent
- Provide contact info
- Be transparent about purpose

### Technical Implementation

```python
class SmartCaptchaSolver:
    """
    Multi-strategy CAPTCHA solver
    Falls back through strategies
    """
    def __init__(self):
        self.strategies = [
            NoCaptchaStrategy(),        # Try without solving
            BehavioralMimicryStrategy(), # Simulate human
            MLSolverStrategy(),          # ML model
            HumanServiceStrategy(),      # 2Captcha fallback
        ]
    
    async def solve(self, page, max_attempts=3):
        """
        Try strategies in order until one works
        """
        for strategy in self.strategies:
            for attempt in range(max_attempts):
                try:
                    result = await strategy.solve(page)
                    if result.success:
                        return result
                except Exception as e:
                    logger.warning(f"{strategy} failed: {e}")
                
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception("All CAPTCHA solving strategies failed")
```

## Ethical Framework

### Questions to Ask

1. **Is this legal?**
   - Check Terms of Service
   - Check Computer Fraud laws in your jurisdiction
   - Consult lawyer for commercial use

2. **Is this ethical?**
   - Why does the CAPTCHA exist?
   - Will my actions harm the site?
   - Am I respecting user privacy?
   - Could this be used maliciously?

3. **Are there alternatives?**
   - Official API?
   - Public datasets?
   - Partnership with site owner?
   - Different data source?

### Red Flags (Don't Do It)

❌ Bypassing login CAPTCHAs for credential stuffing
❌ Bypassing ticket purchase CAPTCHAs (scalping)
❌ Bypassing voting CAPTCHAs (manipulation)
❌ Bypassing contact form CAPTCHAs (spam)
❌ Any site that explicitly prohibits automation

### Maybe Okay (With Permission)

⚠️ Research purposes (academic)
⚠️ Accessibility testing
⚠️ Security research (responsible disclosure)
⚠️ Personal data export (GDPR right)

## Conclusion

CAPTCHA bypass is technically fascinating but ethically complex. The techniques exist and are constantly evolving, but their use requires careful consideration of legal and ethical implications.

**Key Takeaways:**
1. Modern CAPTCHAs are sophisticated, analyzing behavior not just solving puzzles
2. No bypass is 100% reliable
3. Legal and ethical considerations are paramount
4. Often better to work with site owners than against them
5. The arms race will continue

**Remember:** Just because you *can* bypass a CAPTCHA doesn't mean you *should*. Always consider the intent behind the protection and whether your actions align with ethical web scraping practices.

## Further Reading

- "The Science Behind CAPTCHA" (von Ahn et al., 2003)
- "I'm not a human: Breaking the Google reCAPTCHA" (Sivakorn et al., 2016)
- "CAPTCHA: Using Hard AI Problems for Security" (von Ahn et al., 2003)
- Google reCAPTCHA documentation
- Web scraping legal cases (QVC v. Resultly, hiQ v. LinkedIn)

## Next Steps

- Study `06-javascript-rendering.md` for browser automation
- Study `08-rate-limiting.md` for polite scraping
- Study `09-distributed-crawling.md` for scaling

---

**Disclaimer:** This guide is for educational purposes only. The author and contributors are not responsible for misuse of this information. Always comply with applicable laws and terms of service.
