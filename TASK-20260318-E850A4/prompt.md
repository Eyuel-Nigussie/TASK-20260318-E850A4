You are an expert full-stack engineer working under strict company delivery standards.
TASK: Perform Title Screening first (Abandoned/Undoable check)

Title Screening (Abandoned Standard):
1. Dependency on external uncontrollable APIs? (Core functions must call third-party SaaS or mockless external interfaces)
2. Environmental restrictions? (Mandatory Windows system to run)
3. Incomplete title? (Prompt lacks core theme or missing necessary images/link creatives)

Prompt (copy exactly):
The Activity Registration and Funding Audit Management Platform provides an integrated closed-loop management solution in English for applicants, reviewers, financial administrators, and system administrators. Applicants submit registrations through a form wizard built with Vue.js and upload materials item by item according to the checklist. The system validates file types (e.g., PDF/JPG/PNG) and sizes (single file ≤20MB, total ≤200MB) in real time, supports retaining up to three versions of the same material with labels such as "Pending Submission/Submitted/Needs Correction," and automatically locks materials after the deadline. A one-time supplementary submission process (within 72 hours) can still be initiated, with reasons for correction recorded.
Reviewers process applications on the list page based on a state machine workflow: "Submitted-Supplemented-Approved/Rejected-Canceled-Promoted from Waitlist." Batch review (≤50 entries per batch) is supported, along with filling in review comments and viewing traceable logs. Financial administrators record income/expenses in activity details, upload invoice attachments, and generate statistics by category and time. If expenses exceed the budget by 10%, a frontend pop-up warning is triggered, requiring secondary confirmation.
On the system side, FastAPI provides RESTful interfaces. Core data models include registration forms, material checklists and versions, review workflow records, funding accounts/transaction records, data collection batches, and quality validation results. All data is stored locally in PostgreSQL to support pure offline deployment. The backend performs rule-based validation on registrations and materials (type, range, mandatory field consistency), generates quality metrics (approval rate, correction rate, overspending rate), and triggers local alerts when thresholds are exceeded. Files are stored only on local disks, with SHA-256 fingerprints saved for duplicate submission detection. A "similarity/duplicate check" interface is reserved but disabled by default and does not rely on external services.
For security, only username and password login is supported, with passwords stored using strong hashing and salting. Sensitive fields (e.g., ID numbers, contact information) are displayed with role-based masking. Features include access frequency control (account locked for 30 minutes after ≥10 failed attempts within 5 minutes), permission isolation, access auditing, encryption of sensitive configurations, daily local backups, one-click recovery, and support for exporting reconciliation, audit, compliance reports, and whitelist policies for data collection scope.

Step 1: Output the Title Screening result clearly. If it fails, stop and explain why it is Abandoned/Undoable.

Step 2: ALL features in the Prompt are 100% REQUIRED and must be production-grade. Do not half-bake, simplify, mock heavily, or leave any part incomplete.

Step 3: Prioritize implementation in clear tiers:
- Tier 1 (must be perfect before moving on): Authentication, Applicant file upload + versioning + validation, Reviewer state machine + batch review
- Tier 2: Financial admin module (income/expense + budget warning + statistics)
- Tier 3: Quality metrics, auditing, backups, exports, role-based masking, access control

Step 4: Before generating any design files, identify ALL critical architectural decision points. You MUST cover at least these categories:
- Data modeling & database constraints (PK, FK, UNIQUE, INDEXES, soft delete, etc.)
- File storage & deduplication strategy (local disk + SHA-256)
- State machine implementation & concurrency handling
- Authentication & authorization (RBAC model + permission isolation)
- Audit logging & traceability
- Validation strategy (frontend vs backend responsibilities)
- Performance considerations (batch operations ≤50, indexing, large file handling)
- Backup & recovery strategy (daily local backups + one-click recovery)
- Failure handling strategies
- Concurrency control strategy
- System invariants
- Idempotency and retry behavior
- Cross-module integration and consistency

For EACH decision point:
- Propose 2–3 possible approaches
- Select ONE approach
- Justify clearly why it is chosen given the constraints (pure offline, local disk only, Docker, performance, security)

You MUST explicitly define:
- Failure handling strategies for: file upload failures (partial uploads, retries, cleanup), duplicate file detection conflicts (SHA-256), state machine invalid transitions, batch operations (partial success), database constraint violations
- Concurrency control strategy: optimistic vs pessimistic locking, conflict detection and resolution, how concurrent updates to the same entity are handled
- System invariants (enforced at BOTH database level and application level) including but not limited to: file version limits (≤3 per material), total file size limits per application (≤200MB), valid state machine invariants (no illegal state regressions), referential integrity rules across all entities, financial constraints (expenses must belong to a valid activity and respect budget rules)
- Idempotency and retry strategies for: file uploads (prevent duplicate submissions), batch review operations (safe re-execution), financial transactions (no double counting) — include idempotency keys or hashing strategies and safe retry behavior
- All modules MUST integrate correctly. You MUST validate: File uploads are correctly linked to application records and workflow states, State machine transitions enforce business rules across modules, Financial data is consistent with application and activity records, Cross-module invariants are maintained

Step 5: Only AFTER finalizing all architectural decisions, generate:
- The complete docs/design.md which MUST include:
  • Exact DB schema with all constraints (PK, FK, UNIQUE, INDEXES, soft delete, etc.)
  • Explicit state transition rules (allowed + rejected transitions with Mermaid diagram)
  • File storage path structure and naming convention
  • API error handling strategy (standardized responses)
  • Role-permission matrix
  • Folder structure (frontend/ for Vue.js, backend/ for FastAPI, etc.)
  • Testing strategy (unit, integration, API tests) + critical test cases per module (especially Tier 1)
  • Failure handling, concurrency, invariants, idempotency, and cross-module integration strategies
- The initial draft of docs/api-spec.md (all planned endpoints with request/response examples, pagination, and error format)

Step 6: “Production-grade” means:
- No placeholder logic or TODOs
- All constraints enforced at DB and API level
- All critical paths covered by tests
- No silent failures (all errors handled explicitly)

Step 7: Output the full project folder structure.

Step 8: You MUST ask clarification questions specifically about unclear business rules, ambiguous constraints, or missing edge cases.

Step 9: Wait for my approval before starting to code.

Begin now with Step 1 (Title Screening).