import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import json
import os
from datetime import datetime


class BMWScraper:
    def __init__(self):
        self.base_url = "https://www.ss.com/lv/transport/cars/bmw/"
        self.search_url = f"{self.base_url}3-series/filter/"
        self.search_params = {
            "year_min": "2003",
            "year_max": "2008",
            "engine_type": "2",  # 2 is diesel
            "gearbox": "1",  # 1 is manual
            "body_type": "3",  # 3 is universal (wagon)
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.data_file = "seen_ads.json"
        
        # Email settings - replace with your own
        self.sender_email = "main_email@gmail.com"  # CHANGE THIS
        self.sender_password = "passkey"  # CHANGE THIS (use app password for Gmail)
        self.receiver_email = "where to recieve@gmail.com"  # CHANGE THIS
        
        # Load previously seen ads
        self.seen_ads = self.load_seen_ads()
        
        # Store filter criteria for post-filtering
        self.criteria = {
            "year_min": 2003,
            "year_max": 2008,
            "engine": "Dīzelis",  # Diesel in Latvian
            "gearbox": "Manuāla",  # Manual in Latvian
            "body": "Universāls"   # Wagon/Universal in Latvian
        }
    
    def load_seen_ads(self):
        """Load the IDs of previously seen advertisements."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading {self.data_file} - file may be empty or corrupted. Creating new file.")
            # Return empty dict and create a new file
            with open(self.data_file, 'w') as f:
                json.dump({}, f)
            return {}
        return {}
    
    def save_seen_ads(self):
        """Save the IDs of seen advertisements."""
        with open(self.data_file, 'w') as f:
            json.dump(self.seen_ads, f)
    
    def build_search_url(self):
        """Build the search URL with parameters."""
        # First approach - query parameters
        url = self.search_url
        params = []
        for key, value in self.search_params.items():
            params.append(f"{key}={value}")
        
        if params:
            url_with_params = f"{url}?{'&'.join(params)}"
        else:
            url_with_params = url
        
        return url_with_params
    
    def meets_criteria(self, details_text):
        """Check if ad details match our criteria."""
        details_text = details_text.lower()
        
        # Check year
        year_found = False
        for year in range(self.criteria["year_min"], self.criteria["year_max"] + 1):
            if str(year) in details_text:
                year_found = True
                break
        
        # Check engine type (diesel)
        diesel_found = "dīzelis" in details_text.lower() or "diesel" in details_text.lower()
        
        # Check gearbox (manual)
        manual_found = "manuāla" in details_text.lower() or "manual" in details_text.lower()
        
        # Check body type (universal/wagon)
        universal_found = "universāls" in details_text.lower() or "universal" in details_text.lower() or "wagon" in details_text.lower() or "touring" in details_text.lower()
        
        # Return True only if all criteria are met
        return year_found and diesel_found and manual_found and universal_found
    
    def fetch_ads(self):
        """Fetch and parse advertisements from the website."""
        url = self.build_search_url()
        print(f"Checking URL: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Save the HTML to inspect the structure
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # Try multiple selectors to find the ads table
            ads_table = None
            for selector in ['table.filter_tbl', 'form[name="filter_frm"] table', 'table#filter_tbl', 'table#page_main', 'table.d1']:
                ads_table = soup.select_one(selector)
                if ads_table:
                    print(f"Found ads table using selector: {selector}")
                    break
            
            if not ads_table:
                print("Could not find ads table. Trying to find any table...")
                tables = soup.select('table')
                if tables:
                    ads_table = tables[-1]  # Try the last table as fallback
                else:
                    return []
            
            # Try multiple selectors to find ad rows
            ad_rows = []
            for selector in ['tr[id]', 'tr.tr-line', 'tr.r', 'tr[onclick*="window.open"]', 'tr.d1']:
                ad_rows = ads_table.select(selector)
                if ad_rows:
                    print(f"Found {len(ad_rows)} ad rows using selector: {selector}")
                    break
            
            if not ad_rows:
                print("No ad rows found with common selectors. Looking for links...")
                potential_ads = soup.select('a[href*="/msg/"]')
                if potential_ads:
                    print(f"Found {len(potential_ads)} potential ad links")
                    return self.process_ad_links(potential_ads)
                else:
                    return []
            
            return self.process_ad_rows(ad_rows)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching ads: {e}")
            return []
    
    def process_ad_rows(self, ad_rows):
        """Process ad rows to extract details and apply filters."""
        new_ads = []
        
        for row in ad_rows:
            try:
                # Get ad ID
                ad_id = row.get('id', '')
                if not ad_id and 'onclick' in row.attrs:
                    # Try to extract ID from onclick attribute
                    onclick = row['onclick']
                    if '/msg/' in onclick:
                        ad_id = onclick.split('/msg/')[-1].split("'")[0]
                
                if not ad_id:
                    continue
                
                # Skip if already seen
                if ad_id in self.seen_ads:
                    continue
                
                # Extract details - adapt based on the actual structure
                cells = row.select('td')
                if len(cells) < 4:  # Minimum cells needed
                    continue
                
                # Extract title and URL
                title_cell = None
                for cell in cells:
                    if cell.select_one('a'):
                        title_cell = cell
                        break
                
                if not title_cell:
                    continue
                
                title = title_cell.text.strip()
                ad_link = title_cell.select_one('a')
                ad_url = f"https://www.ss.com{ad_link['href']}" if ad_link and 'href' in ad_link.attrs else ""
                
                # Get details from the cells
                details_text = " ".join([cell.text.strip() for cell in cells])
                
                # Extract price
                price = ""
                for cell in reversed(cells):  # Price is usually in one of the last cells
                    if cell.text.strip() and "€" in cell.text:
                        price = cell.text.strip()
                        break
                
                # Apply our own filtering
                if not self.meets_criteria(details_text):
                    print(f"Skipping ad {ad_id} - doesn't meet criteria")
                    continue
                
                # Create ad object
                new_ads.append({
                    'id': ad_id,
                    'title': title,
                    'details': details_text,
                    'price': price,
                    'url': ad_url,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # Mark as seen
                self.seen_ads[ad_id] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            except Exception as e:
                print(f"Error processing ad row: {e}")
        
        return new_ads
    
    def process_ad_links(self, links):
        """Process ad links to extract details and apply filters."""
        new_ads = []
        
        for link in links:
            try:
                href = link.get('href', '')
                if not href or '/msg/' not in href:
                    continue
                
                ad_id = href.split('/msg/')[-1]
                
                # Skip if already seen
                if ad_id in self.seen_ads:
                    continue
                
                # Visit the individual ad page to get full details
                ad_url = f"https://www.ss.com{href}"
                try:
                    ad_response = requests.get(ad_url, headers=self.headers)
                    ad_soup = BeautifulSoup(ad_response.content, 'html.parser')
                    
                    # Extract details
                    title = ad_soup.select_one('h1').text.strip() if ad_soup.select_one('h1') else "BMW 3-Series"
                    
                    # Get all details from the page
                    details_cells = ad_soup.select('tr.d1 td.ads_opt')
                    details_values = ad_soup.select('tr.d1 td.ads_opt_b')
                    
                    details_text = ""
                    for i in range(min(len(details_cells), len(details_values))):
                        details_text += f"{details_cells[i].text.strip()}: {details_values[i].text.strip()}, "
                    
                    # Extract price
                    price_elem = ad_soup.select_one('span.ads_price')
                    price = price_elem.text.strip() if price_elem else ""
                    
                    # Apply our own filtering
                    if not self.meets_criteria(details_text):
                        print(f"Skipping ad {ad_id} - doesn't meet criteria")
                        continue
                    
                    # Create ad object
                    new_ads.append({
                        'id': ad_id,
                        'title': title,
                        'details': details_text,
                        'price': price,
                        'url': ad_url,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Mark as seen
                    self.seen_ads[ad_id] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                except Exception as e:
                    print(f"Error fetching ad details: {e}")
                    continue
                
            except Exception as e:
                print(f"Error processing ad link: {e}")
        
        return new_ads
    
    def send_email(self, new_ads):
        """Send email with new ads."""
        if not new_ads:
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        msg['Subject'] = f"New BMW 3-Series listings ({len(new_ads)} found)"
        
        # Create email body
        body = f"""
        <html>
        <body>
            <h2>Found {len(new_ads)} new BMW listings:</h2>
            <h3>Criteria: BMW 3-Series, years 2003-2008, diesel, manual transmission, wagon/universal body</h3>
        """
        
        for ad in new_ads:
            body += f"""
            <div style="margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                <h3><a href="{ad['url']}">{ad['title']}</a></h3>
                <p><strong>Details:</strong> {ad['details']}</p>
                <p><strong>Price:</strong> {ad['price']}</p>
                <p><a href="{ad['url']}">View Ad</a></p>
            </div>
            """
        
        body += """
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            print(f"Email sent successfully with {len(new_ads)} new listings")
        except Exception as e:
            print(f"Error sending email: {e}")
    
    def save_to_html(self, new_ads):
        """Save new ads to an HTML file instead of sending an email."""
        if not new_ads:
            return
            
        filename = f"new_bmw_ads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>New BMW 3-Series Listings</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .ad {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .ad:hover {{ background-color: #f9f9f9; }}
                h1 {{ color: #333; }}
                a {{ color: #0066cc; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>Found {len(new_ads)} new BMW listings - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>
            <h2>Criteria: BMW 3-Series, years 2003-2008, diesel, manual transmission, wagon/universal body</h2>
        """
        
        for ad in new_ads:
            html_content += f"""
            <div class="ad">
                <h3><a href="{ad['url']}" target="_blank">{ad['title']}</a></h3>
                <p><strong>Details:</strong> {ad['details']}</p>
                <p><strong>Price:</strong> {ad['price']}</p>
                <p><a href="{ad['url']}" target="_blank">View Ad</a></p>
            </div>
            """
            
        html_content += """
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Saved {len(new_ads)} new listings to {filename}")
    
    def run(self, interval_minutes=30, use_email=True):
        """Run the scraper at specified intervals."""
        print(f"Starting BMW ad scraper for SS.com")
        print(f"Filtering for BMW 3-Series, year 2003-2008, diesel, manual, universal body")
        print(f"Will check every {interval_minutes} minutes...")
        
        # Initial test connection
        try:
            test_response = requests.get(self.base_url, headers=self.headers)
            if test_response.status_code == 200:
                print("Successfully connected to SS.com")
            else:
                print(f"Warning: Connection to SS.com returned status: {test_response.status_code}")
        except Exception as e:
            print(f"Error testing connection: {e}")
        
        while True:
            try:
                print(f"\nChecking for new ads at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                new_ads = self.fetch_ads()
                
                if new_ads:
                    print(f"Found {len(new_ads)} new ads matching your criteria!")
                    if use_email:
                        self.send_email(new_ads)
                    else:
                        self.save_to_html(new_ads)
                    self.save_seen_ads()
                else:
                    print("No new ads found matching your criteria")
                
                # Sleep for the specified interval
                print(f"Next check in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\nStopping the scraper...")
                self.save_seen_ads()
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Continuing in 5 minutes...")
                time.sleep(300)


if __name__ == "__main__":
    import argparse
    
    # Create command line arguments
    parser = argparse.ArgumentParser(description='SS.com BMW 3-Series Scraper')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in minutes (default: 30)')
    parser.add_argument('--email', action='store_true', help='Send results via email (default)')
    parser.add_argument('--no-email', action='store_true', help='Save results to HTML file instead of emailing')
    parser.add_argument('--year-min', type=int, default=2003, help='Minimum year (default: 2003)')
    parser.add_argument('--year-max', type=int, default=2008, help='Maximum year (default: 2008)')
    
    args = parser.parse_args()
    
    # Create and run the scraper
    scraper = BMWScraper()
    
    # Update parameters if provided
    if args.year_min:
        scraper.criteria["year_min"] = args.year_min
        scraper.search_params["year_min"] = str(args.year_min)
    if args.year_max:
        scraper.criteria["year_max"] = args.year_max
        scraper.search_params["year_max"] = str(args.year_max)
    
    # Run the scraper
    scraper.run(
        interval_minutes=args.interval,
        use_email=not args.no_email
    )