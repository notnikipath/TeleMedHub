# Optional Improvements Implemented

## Group A: Intelligence

1. **NLP complaint analysis** (`consultation-service /complaints/analyze`):
   - keyword extraction,
   - urgency scoring,
   - specialty suggestions.
2. **Speech-to-protocol auto-fill** (`/speech/protocol`):
   - splits transcript into subjective/objective/plan.
3. **Doctor recommendation by symptoms** (`api-gateway /recommend/doctor`):
   - tag matching + rating + availability score.

## Group B: Integrations

4. **Insurance integration** (`billing-service /insurance/claim` and `/insurance/claims`):
   - digital claims API,
   - approval status handling.

## Group C: Performance

5. **Video server balancing** (`consultation-service /video/nodes`):
   - least-loaded node selection for session start.
6. **EMR cache layer** (`emr-service` with TTL cache):
   - faster repeated reads,
   - target-oriented EMR read metric.
7. **Async file processing** (`consultation-service /sessions/{id}/files`):
   - background upload metadata pipeline.

## Group D: UX

8. **Interactive symptom questionnaire** (`appointment-service /symptoms/questionnaire`):
   - triage risk level,
   - suggested consultation type.
