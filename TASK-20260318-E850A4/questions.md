# Questions & Clarifications Log

**Project:** Activity Registration and Funding Audit Management Platform  
**Date:** 2026-03-25  
**Author:** Eyuel N.

## Logged Questions & Decisions

1. **User Registration / Signup**  
   Q: Is public user signup required?  
   A: No - only seeded accounts are used (sysadmin + role-based pre-seeded users). No signup flow needed.

2. **Role-based Dashboard Navigation**  
   Q: How should users access different role workspaces after login?  
   A: Implemented as tabbed navigation in the dashboard (Applicant / Reviewer / Financial Admin / System Admin tabs) with role-specific views.

3. **File Upload Chunking**  
   Q: How should large files be handled?  
   A: Chunked upload with Content-Range + SHA-256 deduplication, max 20MB per file / 200MB total.

4. **Budget Overrun Handling**  
   Q: Should expense >10% trigger frontend warning?  
   A: Yes - backend returns PENDING_CONFIRMATION + warning payload; frontend shows secondary confirmation.

5. **Backup & Restore**  
   Q: Should restore be in-place?  
   A: Yes - one-click in-place restore with optional pre-restore safety backup.

6. **Supplement Window Rule**  
   Q: Should the supplement window be enforced as strict `deadline + 72h` in code, or is configurable `supplement_deadline` authoritative?  
   A: Strict `submitted_at + 72 hours` (from the moment of submission) is authoritative per the Prompt ("within 72 hours"). The configurable `supplement_deadline` on the activity is used as the outer bound, but the 72-hour window is enforced from the submission timestamp.

7. **Budget Overrun Warning UX**  
   Q: For budget overrun warning, is inline warning + confirm endpoint acceptable, or must UI enforce a blocking modal before first write?  
   A: The Prompt explicitly requires "a frontend pop-up warning is triggered, requiring secondary confirmation". Therefore a blocking modal/pop-up in the frontend is required before the transaction is persisted.

8. **Object-Level Profile Access**  
   Q: For object-level profile access, should non-admin users be limited to self-profile only to satisfy stricter least-privilege expectations?  
   A: Yes. Non-admin users should only be able to read/update their own profile (strict object-level authorization). Other users' profiles are not accessible even with masking, to follow least-privilege and prevent IDOR.

All other business rules (state machine, version limit ≤3, role-based masking, offline Docker deployment, etc.) were implemented exactly as per the original prompt.

No remaining open questions.