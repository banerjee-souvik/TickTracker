from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("")
async def trigger_scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_scan)
    return {"status": "scan started"}


async def _run_scan():
    from agents import scraper_agent, analysis_agent
    await scraper_agent.run()
    await analysis_agent.run()
