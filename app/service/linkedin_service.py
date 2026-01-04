from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Any

from playwright.async_api import async_playwright, Page

from app.config.logger_config import log_user_activity


class LinkedInJobPoster:
    """Class to handle LinkedIn job posting automation"""

    def __init__(self, job_data, user_data_dir="./browser_data"):
        self.job_data = job_data
        self.user_data_dir = user_data_dir
        self.form_link = "https://forms.gle/JW5AcX1zcRgA2ByJ6"

    def generate_job_post_text(self):
        """Generate formatted job post text from job data"""
        data = self.job_data

        # Get company name (you can add this to your JSON or use a default)
        company_name = data.get('company_name', 'Our Company')

        # Format salary
        salary_range = data.get('salary_range', {})
        if salary_range:
            salary = f"{salary_range.get('min', 0):,} - {salary_range.get('max', 0):,} {salary_range.get('currency', 'USD')}"
        else:
            salary = "Competitive salary"

        # Format experience
        experience = data.get('experience', {})
        if experience:
            exp_text = f"{experience.get('min_years', 0)}-{experience.get('max_years', 0)} years"
        else:
            exp_text = "Experience required"

        # Create job post with exact structure requested
        job_post = f"""Company Name: {company_name}

Job Details: {data.get('title', 'Job Title')}
{data.get('description', 'Job description')}

Location: {data.get('location', 'Location not specified')}

Experience: {exp_text}

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
                headless=True,
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


class LinkedInService:
    """Service for LinkedIn operations"""

    def __init__(self):
        pass

    async def post_job_to_linkedin(self, job_data: Dict[str, Any]) -> bool:
        """
        Post a job requirement to LinkedIn

        Args:
            job_data: Dictionary containing job requirement data

        Returns:
            bool: True if posting was successful, False otherwise
        """
        try:
            # Log the LinkedIn posting attempt
            log_user_activity(
                f"Attempting to post job '{job_data.get('title', 'Unknown')}' to LinkedIn",
                action_type="linkedin_job_post_attempt",
                level="info",
            )

            # Create and run the LinkedIn poster
            poster = LinkedInJobPoster(job_data)
            success = await poster.run()

            # Log the result
            if success:
                log_user_activity(
                    f"Successfully posted job '{job_data.get('title', 'Unknown')}' to LinkedIn",
                    action_type="linkedin_job_post_success",
                    level="info",
                )
            else:
                log_user_activity(
                    f"Failed to post job '{job_data.get('title', 'Unknown')}' to LinkedIn",
                    action_type="linkedin_job_post_failure",
                    level="warning",
                )

            return success

        except Exception as e:
            log_user_activity(
                f"Error posting job '{job_data.get('title', 'Unknown')}' to LinkedIn: {str(e)}",
                action_type="linkedin_job_post_error",
                level="error",
            )
            return False
