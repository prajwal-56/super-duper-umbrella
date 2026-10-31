"""Styleguide — every Counting House Ledger component on one page.

Owner: C (KStupid)
Route: /styleguide
Purpose: visual reference for all UI macros and CSS classes during development.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

# No NAV entry — this is a dev-only page.


@router.get("/styleguide", response_class=HTMLResponse)
async def styleguide(request: Request):
    """Render the full design-system styleguide page."""
    return request.app.state.templates.TemplateResponse(
        "styleguide/index.html",
        {"request": request},
    )
