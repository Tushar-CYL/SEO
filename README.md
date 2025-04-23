# SEO AI Generator

A Flask-based AI application for generating SEO meta descriptions and CTAs using advanced language models.

## Features

- **Meta Description Generator**: Create SEO-optimized meta descriptions with three different variations
- **CTA Generator**: Generate compelling calls-to-action that convert visitors
- **Single Entry Mode**: Generate content for individual titles and keywords
- **Bulk Processing**: Upload CSV or Excel files with multiple entries for batch processing
- **AI-Powered**: Uses Perplexity API and Groq (Llama 3) for high-quality content generation

## Installation

1. Clone this repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Set up your environment variables by creating a `.env` file with your API keys:

```
PERPLEXITY_API_KEY=your_perplexity_api_key
GROQ_API_KEY=your_groq_api_key
```

## Usage

1. Start the application:

```bash
python app.py
```

2. Open your browser and navigate to `http://127.0.0.1:5000`

3. Choose between Meta Description or CTA Generator

4. For single entries:
   - Enter your content title and target keyword
   - Click "Generate" to create three unique variations

5. For bulk processing:
   - Prepare a CSV or Excel file with 'title' and 'keyword' columns
   - Upload the file and click "Upload and Generate"
   - Download the results file with generated content

## File Format for Bulk Processing

Your CSV or Excel file should have the following columns:
- `title`: The content title
- `keyword`: The target keyword

A sample template is available in `static/sample_template.csv`.

## API Keys

This application requires API keys from:
- [Perplexity AI](https://www.perplexity.ai/) - For the Sonar model
- [Groq](https://groq.com/) - For the Llama 3 model

## License

This project is licensed under the MIT License - see the LICENSE file for details.
