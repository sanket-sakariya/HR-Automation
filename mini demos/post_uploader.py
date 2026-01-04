import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page

class LinkedInJobPoster:
    def __init__(self, job_data, user_data_dir="./browser_data"):
        self.job_data = job_data
        self.user_data_dir = user_data_dir
        self.form_link = "https://forms.gle/JW5AcX1zcRgA2ByJ6"
        
    def generate_job_post_text(self):
        """Generate formatted job post text from job data"""
        data = self.job_data['data']
        
        # Get company name (you can add this to your JSON or use a default)
        company_name = data.get('company_name', 'Our Company')
        
        # Format salary
        salary = f"${data['salary_range']['min']:,} - ${data['salary_range']['max']:,} {data['salary_range']['currency']}"
        
        # Format experience
        experience = f"{data['experience']['min_years']}-{data['experience']['max_years']} years"
        
        # Create job post with exact structure requested
        job_post = f"""Company Name: {company_name}

Job Details: {data['title']}
{data['description']}

Location: {data['location']}

Experience: {experience}

Salary: {salary}

Apply here: {self.form_link}"""
        
        return job_post
    
    async def post_to_linkedin(self, page: Page, job_post_text: str):
        """Post job to LinkedIn"""
        print("\n🔵 Posting to LinkedIn...")
        
        try:
            # Navigate to LinkedIn
            await page.goto('https://www.linkedin.com/feed/', timeout=60000)
            await asyncio.sleep(4)
            
            # Check if logged in
            current_url = page.url
            if 'login' in current_url or 'checkpoint' in current_url or 'uas' in current_url:
                print("⚠️  Not logged in to LinkedIn...")
                print("⏳ Please log in manually in the browser window...")
                print("⏳ Waiting for you to complete login...")
                
                # Wait for successful login
                try:
                    await page.wait_for_url('**/feed/**', timeout=300000)  # 5 minutes
                    print("✅ Login successful!")
                    await asyncio.sleep(3)
                except:
                    print("⏰ Timeout waiting for login. Please try again.")
                    return False
            
            # Click on "Start a post" button
            print("Opening post composer...")
            start_post_selectors = [
                'button:has-text("Start a post")',
                'button[aria-label*="Start a post"]',
                '.share-box-feed-entry__trigger',
                'button.share-box-feed-entry__trigger',
                '[data-test-id="share-box-trigger"]'
            ]
            
            clicked = False
            for selector in start_post_selectors:
                try:
                    start_post = page.locator(selector).first
                    if await start_post.is_visible(timeout=2000):
                        await start_post.click()
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                print("❌ Could not find 'Start a post' button")
                return False
            
            await asyncio.sleep(3)
            
            # Find and fill the post editor
            print("Typing job post...")
            editor_selectors = [
                'div[role="textbox"][contenteditable="true"]',
                '.ql-editor',
                'div.ql-editor[contenteditable="true"]',
                '[data-placeholder="What do you want to talk about?"]'
            ]
            
            editor_found = False
            for selector in editor_selectors:
                try:
                    editor = page.locator(selector).first
                    if await editor.is_visible(timeout=2000):
                        await editor.click()
                        await asyncio.sleep(1)
                        
                        # Type with delay to avoid detection
                        await editor.type(job_post_text, delay=1)
                        editor_found = True
                        break
                except:
                    continue
            
            if not editor_found:
                print("❌ Could not find post editor")
                return False
            
            await asyncio.sleep(3)
            
            # Click Post button
            print("Finding and clicking Post button...")
            try:
                # Wait for the Post button to be visible and enabled
                post_button = page.locator('button.share-actions__primary-action:has-text("Post")')
                await post_button.wait_for(state='visible', timeout=5000)
                
                # Wait a moment to ensure button is enabled
                await asyncio.sleep(1)
                
                # Click the button
                await post_button.click()
                print("✅ Post button clicked!")
                
                # Wait for 2-3 seconds after posting
                print("⏳ Waiting for post to publish...")
                await asyncio.sleep(3)
                
                # Look for "No thanks" button (post-promotion dialog)
                print("Looking for 'No thanks' button...")
                try:
                    no_thanks_button = page.locator('button.artdeco-button--muted:has-text("No thanks")')
                    await no_thanks_button.wait_for(state='visible', timeout=5000)
                    await no_thanks_button.click()
                    print("✅ Clicked 'No thanks' button")
                    await asyncio.sleep(1)
                except:
                    print("ℹ️  No promotion dialog appeared")
                
            except Exception as e:
                print(f"⚠️  Could not click Post button automatically: {str(e)}")
                print("💡 The post editor is open. Please click 'Post' button manually.")
                input("\n⏸️  Press Enter after you've posted manually...")
                return True
            
            await asyncio.sleep(5)
            print("✅ Job posted to LinkedIn successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error posting to LinkedIn: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run(self):
        """Main execution flow"""
        async with async_playwright() as p:
            # Create user data directory if it doesn't exist
            Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Using browser profile: {self.user_data_dir}")
            print("💡 Your login session will be saved for future use!")
            
            # Launch browser with persistent context (saves login data)
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                viewport={'width': 1080, 'height': 720},
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ],
                ignore_default_args=['--enable-automation'],
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            try:
                # Generate job post text
                job_post_text = self.generate_job_post_text()
                
                print("\n" + "="*60)
                print("📝 Generated Job Post:")
                print("="*60)
                print(job_post_text)
                print("="*60)
                
                # Post to LinkedIn
                print("\n" + "="*60)
                print("Posting to LinkedIn")
                print("="*60)
                
                success = await self.post_to_linkedin(page, job_post_text)
                
                if success:
                    print("\n" + "="*60)
                    print("✅ JOB POSTED SUCCESSFULLY!")
                    print("="*60)
                    print(f"🔗 Application Form: {self.form_link}")
                    print("\n🔒 Closing browser...")
                    await asyncio.sleep(2)
                else:
                    print("\n⚠️  Please check the LinkedIn post manually.")
                    input("\n⏸️  Press Enter to close the browser...")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                await context.close()


# Example usage
async def main():
    # Sample job data - you can load this from API or file
    job_data = {
        "success": True,
        "data": {
            "job_requirement_id": "d82d3ea6-6368-43f7-9e44-a22a3d2e9892",
            "company_id": "aec86343-c950-4be7-a68d-0fa336dd07b2",
            "company_name": "Tech Innovations Inc",  # Add company name here
            "title": "Senior Python Developer",
            "department": "Engineering",
            "description": "We are looking for a Senior Python Developer to join our dynamic team and work on cutting-edge projects.",
            "requirements": [
                {
                    "skill": "Python",
                    "level": "advanced",
                    "required": True
                },
                {
                    "skill": "Django/FastAPI",
                    "level": "intermediate",
                    "required": True
                }
            ],
            "experience": {
                "min_years": 2,
                "max_years": 5,
                "preferred": 3
            },
            "location": "New York, NY",
            "job_type": "full-time",
            "salary_range": {
                "min": 50000,
                "max": 80000,
                "currency": "USD"
            },
            "benefits": [
                "Health Insurance",
                "401k",
                "Remote Work"
            ],
            "status": "draft",
            "is_active": True,
            "created_at": "2026-01-04T02:25:10.804081Z",
            "updated_at": "2026-01-04T02:25:10.804081Z"
        },
        "message": "Job requirement created successfully"
    }
    
    # You can also load from file:
    # with open('job_data.json', 'r') as f:
    #     job_data = json.load(f)
    
    # Create and run job poster
    poster = LinkedInJobPoster(job_data, user_data_dir="./browser_data")
    await poster.run()


if __name__ == "__main__":
    print("🚀 LinkedIn Job Posting Automation")
    print("="*60)
    print("✨ This script will:")
    print("   1. Generate a formatted job post")
    print("   2. Post the job to LinkedIn")
    print("   3. Include your Google Form link")
    print("   4. Save your login for future use")
    print("="*60)
    asyncio.run(main())