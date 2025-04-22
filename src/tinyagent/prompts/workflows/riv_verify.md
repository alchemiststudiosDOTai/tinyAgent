# VERIFY PHASE

You are in the VERIFY phase of a RIV (Reflect-Improve-Verify) process.
Your job is to verify whether the original task has been completed successfully.

## ORIGINAL TASK

{{task_description}}

## EXECUTION HISTORY

{{history_summary}}

## LATEST ACTION RESULT

{{result_text}}

## CREATED/MODIFIED FILES

{{files_info}}

## ERRORS

{{error_text}}

## VERIFICATION INSTRUCTIONS

1. Carefully analyze all available information (original task, action results, and created files)
2. Determine if the task is fully complete by checking:
   - Whether ALL parts of the original task have been accomplished
   - Whether any required outputs (data, files, etc.) have been produced
   - Whether the quality of results meets a reasonable standard
3. Focus on OUTCOMES, not just the process - has the task actually produced what was requested?
4. IMPORTANT: Only mark the task as complete if ALL required outputs exist and meet quality standards
5. Your response MUST be a valid JSON object

## RESPONSE FORMAT

```json
{
  "is_complete": false, // Set to true ONLY if ALL aspects of the task are complete
  "quality": "good | partial | poor", // Assessment of overall result quality
  "reasoning": "Your detailed explanation of why the task is or is not complete",
  "missing_outputs": ["List any specific outputs that are still missing"],
  "next_steps": ["List of recommended next steps if incomplete"]
}
```
