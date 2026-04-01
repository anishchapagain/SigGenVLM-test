"""
Signature Forensic Analysis using Groq API
Model: llama-3.2-11b-vision-preview

This script performs forensic analysis on two signature images to detect:
- Authenticity comparison
- Stroke patterns
- Pressure variations
- Structural similarities/differences
- Potential forgery indicators
"""

import os
import base64
from groq import Groq
from pathlib import Path


def encode_image(image_path):
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def analyze_signatures(signature1_path, signature2_path, api_key=None):
    """
    Perform forensic analysis comparing two signatures
    
    Args:
        signature1_path: Path to first signature image
        signature2_path: Path to second signature image
        api_key: Groq API key (if not set in environment)
    
    Returns:
        Analysis results from the model
    """
    
    # Initialize Groq client
    if api_key:
        client = Groq(api_key=api_key)
    else:
        client = Groq()  # Uses GROQ_API_KEY from environment
    
    # Encode both images
    print("Encoding signature images...")
    signature1_base64 = encode_image(signature1_path)
    signature2_base64 = encode_image(signature2_path)
    
    # Prepare the forensic analysis prompt
    forensic_prompt = """You are a forensic document examiner specializing in signature analysis. 
    
Analyze these two signatures and provide a detailed forensic report covering:

1. **Visual Comparison**:
   - Overall structural similarity
   - Letter formation and proportions
   - Spacing and alignment
   - Size and slant consistency

2. **Stroke Analysis**:
   - Line quality and smoothness
   - Stroke pressure patterns
   - Pen lifts and entry/exit points
   - Natural flow vs. hesitation marks

3. **Unique Characteristics**:
   - Distinctive features in each signature
   - Loop formations and connections
   - Starting and ending strokes
   - Unique flourishes or embellishments

4. **Forensic Indicators**:
   - Signs of tracing or simulation
   - Speed of execution indicators
   - Tremor or unnatural movements
   - Evidence of retouching or correction

5. **Authenticity Assessment**:
   - Probability both signatures are from the same person
   - Key similarities that support authenticity
   - Key differences that raise concerns
   - Overall confidence level (Low/Medium/High)

6. **Conclusion**:
   - Final determination with reasoning
   - Risk factors or red flags identified
   - Recommendation for further analysis if needed

Please provide a comprehensive, professional forensic analysis."""

    print("\nPerforming forensic analysis with Groq API...")
    print(f"Model: llama-3.2-11b-vision-preview\n")
    
    # Make API call with vision model
    try:
        completion = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": forensic_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{signature1_base64}"
                            }
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{signature2_base64}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.3,  # Lower temperature for more focused analysis
            max_tokens=2048,
            top_p=1,
            stream=False
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        return f"Error during analysis: {str(e)}"


def save_report(analysis_result, output_path="forensic_report.txt"):
    """Save the analysis report to a file"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("SIGNATURE FORENSIC ANALYSIS REPORT\n")
        f.write("Model: llama-3.2-11b-vision-preview (Groq API)\n")
        f.write("="*80 + "\n\n")
        f.write(analysis_result)
    print(f"\nReport saved to: {output_path}")


def main():
    """Main execution function"""
    
    # Example usage - Update these paths to your signature images
    SIGNATURE1_PATH = "signature1.jpg"  # Path to first signature
    SIGNATURE2_PATH = "signature2.jpg"  # Path to second signature
    
    # You can set API key here or use environment variable GROQ_API_KEY
    API_KEY = os.getenv("GROQ_API_KEY")
    
    if not API_KEY:
        print("WARNING: GROQ_API_KEY not found in environment variables")
        print("Please set it or provide it directly in the script\n")
    
    # Check if signature files exist
    if not Path(SIGNATURE1_PATH).exists():
        print(f"Error: {SIGNATURE1_PATH} not found")
        print("Please update SIGNATURE1_PATH with your first signature image")
        return
    
    if not Path(SIGNATURE2_PATH).exists():
        print(f"Error: {SIGNATURE2_PATH} not found")
        print("Please update SIGNATURE2_PATH with your second signature image")
        return
    
    print("="*80)
    print("SIGNATURE FORENSIC ANALYSIS")
    print("="*80)
    print(f"Signature 1: {SIGNATURE1_PATH}")
    print(f"Signature 2: {SIGNATURE2_PATH}")
    print("="*80 + "\n")
    
    # Perform analysis
    result = analyze_signatures(SIGNATURE1_PATH, SIGNATURE2_PATH, API_KEY)
    
    # Display results
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80 + "\n")
    print(result)
    
    # Save report
    save_report(result)


if __name__ == "__main__":
    main()