You're an **expert Generative AI engineer and product manager as well.**
You have 4-5years of exposure in product developemtn in top FinTech organizations.

I want you to draft a plan paper for the application scope below:
a. Prepare a file **plan.md** with concise technical and business aspects, with application in production in mind.
b. This draft will be used to design and develop the application.
c. FastAPI will be used for the application.

Here are the parties involved:
1. **NepaliWorld**: The developer of the application.
2. **FinTech-Nepal**: The users of the application.
3. **Server**: The server that will host the application.
4. **OpenAI-o3.1**: The API that will be used for processing.

Here's my plan about the application now:
1. Building a **Signature verification system** for FinTech-Nepal.
2. Providing the client API access to FinTech-Nepal.
3. Using cloud based API like **Gemini API** or **OpenAI API Key** for processing.

How the project will operate:
1. FinTech-Nepal will use my provided API to connect to my server.
2. Server will use OpenAI-o3.1 API to process the signature verification request.
3. Server will return the result to FinTech-Nepal.

How Server will use OpenAI-o3.1 API to process the signature verification request:
1. FinTech-Nepal will send the signatures of the customer (1 Genuine + 1 Forged or attempted forgery) to the server.
2. Server will do necessary validation on the signature image. (max file size, min file size, valid image format, etc.)
3. Server will send both signature image to the OpenAI-o3.1 API.
4. OpenAI-o3.1 API will process the signature image and return the result to the server.
    4.1 Result will be in the form of JSON. (strict)
    4.2 Result will contain the Score (0-100) and Verdict (Genuine/Forged).
    4.3 Certain forensic related information will be included in the result. (e.g. line quality, slant, human-like description, sentiment, etc.)
5. Server will return the result to, without any reference to OpenAI-o3.1 API to FinTech-Nepal.

Follow few strict analysis process as below and more as you see fit:
1. **Letter structure** – Do the signatures contain the same letters / characters? If the names differ or the overall shape is completely different, the query is FORGED.
2. **Line quality** – Smooth natural flow vs. shaky/forced drawing.
3. **Slant & proportion** – Consistency of angle and size.
4. **Terminal strokes** – Tapered/fluid vs. blunt/heavy.
5. **Overall match** – Exact, near‑exact, or clearly different.
6. Is the signature looks like being drawn by a human or a machine?
7. Is the signature looks like being made in a hurry or slowly?
8. Is the signature seems to be copied for fraud or forgery?
9. Is the signature seems to be made under some situational pressure?
10. and many more..

JSON Format:  
{
  "verdict": "Genuine" | "Forged",
  "score": integer (0–100),
  "characteristics": [
        "<2-3 word label>",
        "<2-3 word label>",
        "<2-3 word label>",
        "<2-3 word label>",
        "<2-3 word label>"
  ]
}

Note: 
1. **characteristics** should be in the form of 2-3 word labels with real alike forensic analysis based messages.
2. **OpenAI-o3.1** should not be mentioned anywhere in the output.
2.1 All necessary guardrails should be in place to prevent any kind of malicious use.
2.2 Output should be in JSON format.

LLM, VLM are not specialized in signature verification. But, we can use them for signature verification in a kind of forensic analysis.

But the final output should resemble to my use case and business requirements.

This is an Generative AI based application, so it will not be 100% accurate. But it will be close to 100% accurate.

Production will take place as API based.
May be we need to use multiple API to get the best result or in case of fallback.
Address all API driven issues and concerns.

I want to make this application failure less and result driven.
DB related schema, fully optimized and production ready.
Logs related to the application should be stored in a file and should be rotated based on the size and time.
Fully configurable application, is expected.