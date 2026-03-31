# Signature Verification System Plan Paper 
**Project Name:** GenSigLLM
**Developer:** NepaliWorld
**Target User:** FinTech-Nepal

## 1. Executive Summary
**GenSigLLM** is an advanced, API-first Generative AI forensic signature verification system designed to automate and augment the detection of signature forgery. Built with the high-stakes environment of FinTech-Nepal in mind, the system leverages state-of-the-art Vision-Language Models (VLMs) like OpenAI-o3.1 to provide a forensic-grade analysis of signature similarity. This document outlines the technical architecture, business operational scope, and production-ready safeguards necessary to build a highly available, robust verification API.

## 2. Business Scope & System Workflow
### 2.1 Operational Pipeline
1. **Client Interaction:** FinTech-Nepal integrates our REST API. Upon processing a transaction, the client securely posts two signature images (1 known Genuine, 1 Questioned/Attempted) to the GenSigLLM Server.
2. **Preprocessing Validation:** The server strictly validates payload metrics before triggering the expensive AI engine.
    *   **Size & Dimensions:** Min/Max file size limits (e.g., 10KB to 5MB), enforcing resolution minimums.
    *   **Format & Integrity:** Acceptable formats restricted to PNG, JPEG, WEBP. Checks for MIME type spoofing and decodability validation.
3. **AI Forensic Engine:** The server securely proxies the images alongside heavily engineered forensic prompts to the AI Provider (OpenAI-o3.1).
4. **Abstracted Response Formulation:** The server parses the response strictly into the predefined JSON format, entirely abstracting the underlying AI capabilities from the client.
5. **Human-In-The-Loop (HITL) Integration:** The structured AI forensic output is presented to a designated human operator at FinTech-Nepal via their internal systems. The generative AI acts as an augmented intelligence layer, assisting the operator but requiring a final "human-level review" and sign-off before a transaction is conclusively approved or rejected.

### 2.2 Security, API Keys & Compliance Guardrails
*   **Secure API Key Distribution & Sharing:** FinTech-Nepal clients will generate their API credentials via a secure developer portal or receive them out-of-band securely via encrypted channels. Only the hashed representations (`api_key_hash`) are ever stored in our database. API payloads must pass these keys via the `Authorization: Bearer <token>` header or `x-api-key` header.
*   **White-labeling Model Usage:** Any reference to OpenAI-o3.1 or competing foundation models is entirely stripped from headers, errors, and responses. The client interfaces strictly with "GenSigLLM API".
*   **Prompt Injection Mitigation:** Hardened API boundaries to prevent anomalous image payloads or metadata manipulation attempting to hijack the AI instructions.

## 3. Technical Architecture
### 3.1 Stack
*   **Application Framework:** FastAPI (Python) - selected for async performance, automatic OpenAPI documentation, and robust Pydantic data validation.
*   **Database:** PostgreSQL (Relational) via SQLAlchemy ORM or SQLModel.
*   **Processing Engine:** OpenAI-o3.1 (Primary) with structured JSON Output capabilities.
*   **Internal Admin Dashboard (NepaliWorld):** A secured internal web interface (e.g., React/Next.js or Streamlit) pointing to protected admin-only FastAPI routes to govern the system.

### 3.2 Internal Admin Features
*   **Client Management:** Onboarding FinTech-Nepal clients, issuing/revoking API keys, and modifying usage tiers.
*   **Telemetry & Observability:** Monitoring live API traffic, tracking Fallback AI trigger events, inspecting error frequency, and auditing `verification_logs`.
*   **Configuration Control:** A GUI to hot-swap `.env` parameters without server restarts.

### 3.3 Resilience & High Availability
To ensure a failure-less, result-driven experience:
*   **Circuit Breakers & Fallbacks:** If OpenAI-o3.1 experiences an outage, rate limits, or degradation, the server will smoothly fallback to an alternate VLM (e.g., Gemini Pro Vision) utilizing a matching prompt template.
*   **Retry with Exponential Backoff:** Network instability or transient errors during AI API calls will trigger scheduled, delayed retries automatically.

## 4. Analytical Forensic Parameters
The AI instructions enforce strict evaluation against standard forensic document examination criteria:
1. **Letter Structure:** Analysis of character alignment and baseline deviation.
2. **Line Quality:** Assessment of fluid, natural flow versus shaky, forced, or labored drawings.
3. **Slant & Proportion:** Ratio and angular consistency mapping.
4. **Terminal Strokes:** Fluid, tapered endpoints compared to blunt or heavy stops.
5. **Execution Velocity:** Detection of rapid habitual signing versus slow, cautious calculation.
6. **Situational Aberrations:** Identification of stress, hesitation, or non-habitual characteristics.
7. **Human-like vs Machine-like:** Assessment of whether the signature appears to be drawn by a human or a machine.
8. **Hurry vs Slow:** Assessment of whether the signature appears to be made in a hurry or slowly.
9. **Copy vs Forgery:** Assessment of whether the signature appears to be copied for fraud or forgery.
10. **Situational Pressure:** Assessment of whether the signature appears to be made under some situational pressure.

## 5. Output Specification
All outputs are strictly serialized to ensure JSON consistency, guaranteeing downstream client parsers receive reliable formats.

```json
{
  "verdict": "Genuine",
  "score": 92,
  "characteristics": [
    "The overall structural alignment matches exactly with the provided reference.",
    "The signature exhibits a fluid, natural flow heavily indicative of habitual signing.",
    "Terminal strokes are matching with swift, tapered endpoints.",
    "Height proportions across the entire signature are consistently accurate."
  ]
}
```

*Note: The format of `characteristics` is entirely configurable via the application settings (e.g. `CHARACTERISTICS_FORMAT`). It can be toggled between concise labels (2-3 words) or descriptive context (full sentences, as shown above) depending on FinTech-Nepal's requirements.*

## 6. Database Schema Design (PostgreSQL)
Optimized for high-throughput relational persistence and comprehensive auditing. 

*   **`admin_users`**: `id`, `username`, `password_hash`, `role`, `created_at` (for NepaliWorld internal team access).
*   **`clients`**: `id`, `api_key_hash`, `organization_name`, `tier`, `is_active`, `created_at`.
*   **`verification_logs`**: `id`, `client_id`, `transaction_reference`, `score`, `verdict`, `human_reviewed_verdict` (Nullable, populated via post-back when HITL review finishes), `processing_time_ms`, `http_status_code`, `timestamp`. 
    *   *(For compliance, actual images may be immediately discarded post-inference or held transiently in secure S3 storage based on data laws, logging only reference IDs).*
*   **`error_telemetry`**: `id`, `log_id`, `provider_used`, `error_type`, `stack_trace`, `timestamp`. (Tracks fallback events and internal ML costs).

## 7. Advanced Configuration & Error Management
Error management and high configurability are the core paradigms of GenSigLLM.
*   **Centralized Configuration Engine:** Utilizing `pydantic-settings` to govern the entire application via a `.env` file or environment variables. Properties such as `CHARACTERISTICS_FORMAT`, `FALLBACK_RETRY_ATTEMPTS`, `MAX_IMAGE_SIZE_MB`, `PRIMARY_LLM_PROVIDER`, and `LLM_TIMEOUT_SECONDS` can be modified on the fly without deployment or code alterations.
*   **Granular Error Handling:**
    *   **Input Handling (400 Levels):** Precise JSON error responses pointing out exact image validation failures (e.g., "File exceeds 5MB limit" or "Invalid image aspect ratio").
    *   **Server Handling (500 Levels):** If the primary AI provider (OpenAI) returns a 5XX error, rate limiting (429), or times out, GenSigLLM suppresses the upstream error, actively logs the `error_telemetry`, and immediately triggers the **Fallback Protocol** routing the same payload to the secondary VLM smoothly.
*   **Robust Logging:** Implementation using native `logging` or `loguru` configured with a `RotatingFileHandler`. Log files run through a `RotatingFileHandler` configured to rotate by both **size limit (e.g., 50MB)** and **time (daily at midnight)**. Old logs are automatically archived and retained for a set policy period.

## 8. Summary
**GenSigLLM** positions itself as a fault-tolerant, API-centric forensic middleware. By sandwiching raw Generative VLMs between robust validation layers, caching, and rigorous fallback protocols, NepaliWorld delivers a dependable, high-fidelity security integration for FinTech-Nepal.
