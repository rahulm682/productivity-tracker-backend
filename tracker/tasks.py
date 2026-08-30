import logging
from django.conf import settings
from django.core.cache import cache
from celery import shared_task

from .models import BrowsingSession
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger('tracker')

class IntentClassification(BaseModel):
    category: str = Field(description="Must be exactly one of: [Focused Work, Learning, Entertainment, Unstructured Browsing]")
    reasoning: str = Field(description="One concise sentence explaining why this workflow block was classified this way, citing specific physical actions (e.g., keystrokes) or content snippets.")
    confidence_score: int = Field(description="Confidence level of this classification from 0 to 100.", ge=0, le=100)


@shared_task
def dispatch_device_classification_jobs():
    """
    Finds active devices and pushes tasks to Redis ONLY if 
    there isn't already a task queued or running for that device.
    """
    active_device_ids = BrowsingSession.objects.filter(
        ai_intent__isnull=True
    ).values_list('device_id', flat=True).distinct()
    
    if not active_device_ids:
        return "No unclassified sessions found."

    dispatched_count = 0

    for device_id in active_device_ids:
        lock_key = f"lock:queued_device:{device_id}"
        
        is_new_task = cache.add(lock_key, "true", timeout=600)
        
        if is_new_task:
            classify_device_workflow.delay(device_id)
            dispatched_count += 1
        else:
            logger.info(f"Device {device_id} already has a task queued or running. Skipping push.")

    return f"Dispatched {dispatched_count} new tasks (Skipped duplicates)."


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def classify_device_workflow(self, device_id):
    """
    Processes the chronological workflow exclusively for a single device.
    Loops until the device's backlog is cleared.
    """
    lock_key = f"lock:queued_device:{device_id}"
    total_processed = 0

    try:
        while True:
            unclassified_sessions = list(
                BrowsingSession.objects.filter(device_id=device_id, ai_intent__isnull=True)
                .order_by('start_time')[:20]
            )

            if not unclassified_sessions:
                break

            # model_name="openai/gpt-oss-120b",     
            # Upgraded to Llama 3.3 70B Versatile
            llm = ChatGroq(
                temperature=0.1, 
                model_name="openai/gpt-oss-120b", 
                api_key=settings.GROQ_API_KEY,
                max_tokens=1024
            )
            parser = PydanticOutputParser(pydantic_object=IntentClassification)

            prompt = PromptTemplate(
                template="""You are an analytical engine categorizing user browsing sessions based on granular behavioral telemetry.

                Analyze the following continuous block of web browsing activity.
                Determine the DOMINANT intent of this workflow.
                
                ### Interpretation Rules:
                *   Focused Work: Characterized by high keystrokes, active engagement scores, and development environments (e.g., localhost, IDEs, AWS consoles).
                *   Learning: Characterized by high scrolling, moderate-to-low typing, and reading technical documentation or tutorials (look at H1 and Snippet).
                *   Entertainment: Characterized by high background audio/video, long active durations, and minimal physical inputs (clicks/keystrokes).
                *   Unstructured Browsing: Fast context switching, low engagement scores, and short durations across diverse domains (e.g., social media feeds).
                
                Chronological Browsing Log:
                {browsing_history}
                
                {format_instructions}
                """,
                input_variables=["browsing_history"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )
            
            chain = prompt | llm | parser

            history_lines = []
            for s in unclassified_sessions:
                meta = s.metadata or {}
                content = meta.get('content', {})
                h1 = content.get('h1', 'None')
                snippet = content.get('snippet', 'None')
                is_local = content.get('is_localhost', False)
                
                keys = getattr(s, 'keystrokes', 0)
                clicks = getattr(s, 'clicks', 0)
                scrolls = getattr(s, 'scrolls', 0)
                
                line = (
                    f"- Domain: {s.domain} (Localhost: {is_local}) | "
                    f"Title: {meta.get('title', 'Unknown')} | H1: {h1} | Snippet: {snippet[:75]}... | "
                    f"Active: {s.active_duration_seconds}s | Audio: {s.background_audio_seconds}s | "
                    f"Keys: {keys} | Clicks: {clicks} | Scrolls: {scrolls} | IPM: {s.engagement_score}"
                )
                history_lines.append(line)
                
            history_text = "\n".join(history_lines)
            
            logger.info(f"Classifying chunk of {len(unclassified_sessions)} sessions for device {device_id}...")
            result = chain.invoke({"browsing_history": history_text})
            
            chunk_ids = [s.id for s in unclassified_sessions]
            BrowsingSession.objects.filter(id__in=chunk_ids).update(
                ai_intent=result.category
            )
            
            total_processed += len(unclassified_sessions)
            logger.info(f"Device {device_id} Verdict: {result.category} (Confidence: {result.confidence_score}%) - {result.reasoning}")

        cache.delete(lock_key)
        return f"Successfully processed {total_processed} sessions for {device_id}."

    except Exception as e:
        logger.error(f"Error classifying device {device_id}: {str(e)}")
        raise self.retry(exc=e)
