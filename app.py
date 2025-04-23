import os
import pandas as pd
import tempfile
import gc  # For garbage collection
import time  # For adding delays
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.utils import secure_filename
import langchain
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
import requests
import json
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xls', 'xlsx'}
app.config['SESSION_TYPE'] = 'filesystem'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # Limit upload size to 5MB

# API Keys
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Initialize Groq LLM
groq_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name="llama3-70b-8192"
)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def search_perplexity(title, keyword):
    """Search using Perplexity API for additional context with retry logic"""
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar",
        "query": f"SEO meta description for '{title}' focusing on keyword '{keyword}'",
        "options": {"stream": False}
    }
    
    # Add retry logic for API stability
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=10  # Add timeout to prevent hanging
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
            else:
                return f"Using keyword '{keyword}' for SEO optimization."  # Fallback content
        except Exception as e:
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                time.sleep(retry_delay * (attempt + 1))
                continue
            return f"Using keyword '{keyword}' for SEO optimization."  # Fallback content
    
    return f"Using keyword '{keyword}' for SEO optimization."  # Final fallback

def generate_meta_description(title, keyword, target_length=150, style=None):
    """Generate meta description using LLM with character count validation"""
    if style is None:
        style = {
            'desc': 'compelling',
            'approach': 'Focus on benefits and unique value'
        }
    
    banned_words_and_phrases = [
        "Unlock", "Unleash", "Supercharge", "Leverage", "Empower", "Transform", "Transformative", 
        "Revolutionize", "Amplify", "Maximize", "Elevate", "Disrupt", "Drive change", "Turbocharge", 
        "Ignite", "Game-changer", "Secret weapon", "Arsenal", "Superpowers", "Lighthouse", "Magic", 
        "Buzzword", "Puzzle", "Toolbox", "Journey", "Landscape", "Ecosystem", "Strategy", "Integrity",
        "Savvy", "Cutting-edge", "Next-gen", "Innovative", "Powerful", "Essential", "Crucial", 
        "Disruptive", "Seamless", "Limitless", "Scalable", "In today's world", "In conclusion", 
        "Unlock the power of", "Shouting into the void", "Stop doing X. Start doing Y", 
        "Where the magic happens", "Light up your funnel", "Revolutionize your", 
        "Become a superstar", "A double-edged sword", "It's not about X. It's about Y", 
        "Take your to the next level", "At the end of the day", "Soar to new heights", 
        "Skyrocket your", "Crickets", "Stand out from the noise", "Thank you for it",
        "It's important to", "It's vital that", "There's no denying that", 
        "It goes without saying", "The reality is", "This article will help you", 
        "We live in a world where", "This blog explores", "In this post, you'll discover"
    ]
    
    # Get additional context from Perplexity
    perplexity_context = search_perplexity(title, keyword)
    
    # Create prompt for meta description with strict character count requirements
    prompt = f"""You are an SEO expert. Generate a UNIQUE {style['desc']} meta description that is COMPLETELY DIFFERENT from others:

Title: {title}
Keyword: {keyword}
Target Length: EXACTLY {target_length} characters

STYLE REQUIREMENTS:
- {style['approach']}
- Never start the same way as other descriptions
- Use unique sentence structures
- Use fresh, original language

STRICT RULES:
1. MUST be BETWEEN 120-160 characters, with {target_length} as the ideal target
2. Include '{keyword}' naturally but differently
3. Use active voice only
4. NO duplicate words from title except the keyword
5. Create a UNIQUE value proposition
6. NEVER use any of these banned words and phrases: {', '.join(banned_words_and_phrases)}
7. Count the characters PRECISELY - this is critical

Additional context from research:
{perplexity_context}

Output ONLY the meta description text. Do not include any explanations or character counts."""
    
    # Generate meta description using Groq
    response = groq_llm.invoke(prompt)
    
    # Clean up the response to remove any prefixes or explanations
    meta_description = response.content.strip()
    
    # Remove common prefixes that might appear in the output
    prefixes_to_remove = [
        "Here is the meta description:", "Here's the meta description:",
        "Meta description:", "Here is a meta description:",
        "Here's a meta description:", "The meta description is:",
        "Here is the revised meta description:", "Revised meta description:",
        "Here's the revised meta description:"
    ]
    
    for prefix in prefixes_to_remove:
        if meta_description.lower().startswith(prefix.lower()):
            meta_description = meta_description[len(prefix):].strip()
    
    # Remove any quotes that might be around the text
    meta_description = meta_description.strip('"').strip("'").strip()
    
    # Validate and adjust character count
    attempts = 0
    max_attempts = 2
    
    while attempts < max_attempts:
        char_count = len(meta_description)
        
        # If character count is within acceptable range, return it
        if 120 <= char_count <= 160:
            return meta_description
        
        # If too short, ask to expand
        elif char_count < 120:
            adjust_prompt = f"""The meta description is too short at {char_count} characters. 
            Expand it to be between 120-160 characters while maintaining the same meaning and style:
            
            Current description: {meta_description}
            
            Output ONLY the revised meta description with no explanations, prefixes, or quotes."""
            
            response = groq_llm.invoke(adjust_prompt)
            meta_description = response.content.strip()
        
        # If too long, ask to trim
        elif char_count > 160:
            adjust_prompt = f"""The meta description is too long at {char_count} characters. 
            Trim it to be between 120-160 characters while maintaining the same meaning and style:
            
            Current description: {meta_description}
            
            Output ONLY the revised meta description with no explanations, prefixes, or quotes."""
            
            response = groq_llm.invoke(adjust_prompt)
            meta_description = response.content.strip()
        
        attempts += 1
    
    # If still not within range after attempts, perform manual truncation or expansion
    char_count = len(meta_description)
    if char_count > 160:
        meta_description = meta_description[:157] + '...'
    elif char_count < 120:
        # Add a generic ending if too short
        meta_description += " Learn more about " + keyword + " today."
        # Truncate if it became too long
        if len(meta_description) > 160:
            meta_description = meta_description[:157] + '...'
    
    return meta_description

def generate_cta_content(title, keyword):
    """Generate CTA using LLM"""
    banned_words_and_phrases = [
        "Unlock", "Unleash", "Supercharge", "Leverage", "Empower", "Transform", "Transformative", 
        "Revolutionize", "Amplify", "Maximize", "Elevate", "Disrupt", "Drive change", "Turbocharge", 
        "Ignite", "Game-changer", "Secret weapon", "Arsenal", "Superpowers", "Lighthouse", "Magic", 
        "Buzzword", "Puzzle", "Toolbox", "Journey", "Landscape", "Ecosystem", "Strategy", "Integrity",
        "Savvy", "Cutting-edge", "Next-gen", "Innovative", "Powerful", "Essential", "Crucial", 
        "Disruptive", "Seamless", "Limitless", "Scalable", "In today's world", "In conclusion", 
        "Unlock the power of", "Shouting into the void", "Stop doing X. Start doing Y", 
        "Where the magic happens", "Light up your funnel", "Revolutionize your", 
        "Become a superstar", "A double-edged sword", "It's not about X. It's about Y", 
        "Take your to the next level", "At the end of the day", "Soar to new heights", 
        "Skyrocket your", "Crickets", "Stand out from the noise", "Thank you for it"
    ]
    
    # Create prompt for CTA generation
    prompt = f"""You are a conversion rate optimization expert. Generate a compelling call-to-action (CTA) for:

Title: {title}
Keyword: {keyword}

REQUIREMENTS:
- Create a UNIQUE and COMPELLING call-to-action
- Focus on creating urgency and value
- Keep it concise (1-2 sentences maximum)
- Include '{keyword}' naturally
- Use active voice and direct address
- Be specific about the benefit/value
- NEVER use any of these banned words and phrases: {', '.join(banned_words_and_phrases)}

Output ONLY the CTA text. Do not include any explanations, prefixes, or quotes."""
    
    # Generate CTA using Groq
    response = groq_llm.invoke(prompt)
    
    # Clean up the response to remove any prefixes or explanations
    cta = response.content.strip()
    
    # Remove common prefixes that might appear in the output
    prefixes_to_remove = [
        "Here is the CTA:", "Here's the CTA:",
        "CTA:", "Here is a CTA:",
        "Here's a CTA:", "The CTA is:",
        "Call-to-action:", "Here is the call-to-action:",
        "Here's the call-to-action:"
    ]
    
    for prefix in prefixes_to_remove:
        if cta.lower().startswith(prefix.lower()):
            cta = cta[len(prefix):].strip()
    
    # Remove any quotes that might be around the text
    cta = cta.strip('"').strip("'").strip()
    
    return cta

def process_file(file_path, generation_type):
    """Process uploaded file and generate meta descriptions or CTAs with memory optimization"""
    try:
        # Read the file - use chunksize for large files to reduce memory usage
        if file_path.endswith('.csv'):
            # Read only first 10 rows to check columns and create structure
            df_sample = pd.read_csv(file_path, nrows=10)
        else:
            # Read only first 10 rows to check columns and create structure
            df_sample = pd.read_excel(file_path, nrows=10)
        
        # Check required columns
        if 'title' not in df_sample.columns or 'keyword' not in df_sample.columns:
            return None, "Error: File must contain 'title' and 'keyword' columns."
        
        # Create directory for output if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Create a unique filename
        filename = f"{generation_type}_results_{uuid.uuid4().hex[:8]}.csv"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Process in small batches to reduce memory usage
        # First create the output file with headers
        if generation_type == 'meta':
            columns = ['title', 'keyword', 'Meta Description 1', 'Meta Description 2', 'Meta Description 3']
        else:
            columns = ['title', 'keyword', 'CTA 1', 'CTA 2', 'CTA 3']
            
        # Create empty output file with headers
        pd.DataFrame(columns=columns).to_csv(output_path, index=False)
        
        # Process in small batches
        batch_size = 3  # Very small batch size for strict memory constraints
        total_rows = 0
        
        # Process CSV or Excel in chunks
        if file_path.endswith('.csv'):
            for chunk in pd.read_csv(file_path, chunksize=batch_size):
                process_chunk(chunk, generation_type, output_path)
                total_rows += len(chunk)
        else:
            # Excel doesn't support chunking directly, so we'll read in small batches
            excel_file = pd.ExcelFile(file_path)
            sheet_name = excel_file.sheet_names[0]  # Get first sheet
            
            # Get total rows
            total_excel_rows = excel_file.book.sheet_by_name(sheet_name).nrows - 1  # Subtract header
            
            # Process in batches
            for start_row in range(1, total_excel_rows + 1, batch_size):  # Start from 1 to skip header
                end_row = min(start_row + batch_size, total_excel_rows + 1)
                chunk = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=range(1, start_row), nrows=end_row-start_row)
                
                # Add headers if this is the first chunk
                if start_row == 1:
                    chunk.columns = df_sample.columns
                    
                process_chunk(chunk, generation_type, output_path)
                total_rows += len(chunk)
        
        return filename, f"Successfully processed {total_rows} rows."
    except Exception as e:
        return None, f"Error processing file: {str(e)}"

def process_chunk(chunk, generation_type, output_path):
    """Process a small chunk of data to reduce memory usage"""
    # Create a result dataframe for this chunk
    result_chunk = chunk.copy()
    
    # Process each row in the chunk
    for idx, row in result_chunk.iterrows():
        title = row['title']
        keyword = row['keyword']
        
        if generation_type == 'meta':
            # Generate meta descriptions one at a time to reduce memory usage
            for i in range(1, 4):
                meta = generate_meta_description(title, keyword)
                result_chunk.at[idx, f'Meta Description {i}'] = meta
                # Force garbage collection to free memory
                gc.collect()
        else:
            # Generate CTAs one at a time
            for i in range(1, 4):
                cta = generate_cta_content(title, keyword)
                result_chunk.at[idx, f'CTA {i}'] = cta
                # Force garbage collection to free memory
                gc.collect()
    
    # Append to the CSV file without loading the whole file into memory
    result_chunk.to_csv(output_path, mode='a', header=False, index=False)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_meta', methods=['GET', 'POST'])
def generate_meta():
    if request.method == 'POST':
        # Check if single input or file upload
        if 'title' in request.form and 'keyword' in request.form:
            title = request.form['title']
            keyword = request.form['keyword']
            
            # Generate 3 different meta descriptions
            meta1 = generate_meta_description(title, keyword)
            meta2 = generate_meta_description(title, keyword)
            meta3 = generate_meta_description(title, keyword)
            
            return render_template('meta_results.html', title=title, keyword=keyword, 
                                  meta1=meta1, meta2=meta2, meta3=meta3)
        
        # File upload
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash('No file selected')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Process file
                output_file, message = process_file(file_path, 'meta')
                if message and "Error" in message:
                    flash(message)
                    return redirect(request.url)
                elif message:
                    flash(message)
                
                # Show download link page
                return render_template('download.html', 
                                      filename=output_file, 
                                      message=message, 
                                      download_url=url_for('download_file', filename=output_file))
    
    return render_template('generate_meta.html')

@app.route('/generate_cta', methods=['GET', 'POST'])
def generate_cta():
    if request.method == 'POST':
        # Check if single input or file upload
        if 'title' in request.form and 'keyword' in request.form:
            title = request.form['title']
            keyword = request.form['keyword']
            
            # Generate 3 different CTAs
            cta1 = generate_cta_content(title, keyword)
            cta2 = generate_cta_content(title, keyword)
            cta3 = generate_cta_content(title, keyword)
            
            return render_template('cta_results.html', title=title, keyword=keyword, 
                                  cta1=cta1, cta2=cta2, cta3=cta3)
        
        # File upload
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash('No file selected')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Process file
                output_file, message = process_file(file_path, 'cta')
                if message and "Error" in message:
                    flash(message)
                    return redirect(request.url)
                elif message:
                    flash(message)
                
                # Show download link page
                return render_template('download.html', 
                                      filename=output_file, 
                                      message=message, 
                                      download_url=url_for('download_file', filename=output_file))
    
    return render_template('generate_cta.html')

# Dedicated download route
@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            flash("File not found. Please try again.")
            return redirect(url_for('index'))
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
    except Exception as e:
        flash(f"Download error: {str(e)}")
        return redirect(url_for('index'))

# Ensure upload directory exists at startup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure for Railway deployment
if __name__ == '__main__':
    # Get port from environment variable for Railway compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
# Add a route to check server health
@app.route('/health')
def health_check():
    memory_info = {}
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = {
            "memory_percent": process.memory_percent(),
            "memory_info": str(process.memory_info())
        }
    except ImportError:
        memory_info = {"status": "psutil not installed"}
        
    return {
        'status': 'healthy',
        'memory': memory_info,
        'environment': 'railway'
    }, 200
