from celery import shared_task


@shared_task(bind=True)
def test_agency_management_task(self):
    """
    Minimal health-check task for the Agency Management app.
    """
    return {"status": "SUCCESS", "message": "Agency Management task executed successfully"}