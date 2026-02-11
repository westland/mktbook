"""HTML page routes."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from mktbook.db import queries
from mktbook.web.app import TEMPLATES

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    bots = await queries.get_all_bots()
    grades = await queries.get_latest_grades()
    bot_map = {b.id: b for b in bots}
    leaderboard = []
    for g in grades:
        bot = bot_map.get(g.bot_id)
        leaderboard.append({
            "bot_name": bot.bot_name if bot else "Unknown",
            "student_name": bot.student_name if bot else "Unknown",
            "overall_score": g.overall_score,
            "bot_id": g.bot_id,
        })
    recent_messages = await queries.get_messages(limit=20)
    return TEMPLATES.TemplateResponse("dashboard.html", {
        "request": request,
        "bots": bots,
        "leaderboard": leaderboard,
        "messages": recent_messages,
    })


@router.get("/bots", response_class=HTMLResponse)
async def bot_list(request: Request) -> HTMLResponse:
    bots = await queries.get_all_bots()
    stats = {}
    for b in bots:
        stats[b.id] = await queries.get_bot_stats(b.id)
    return TEMPLATES.TemplateResponse("bot_list.html", {
        "request": request,
        "bots": bots,
        "stats": stats,
    })


@router.get("/bots/new", response_class=HTMLResponse)
async def bot_form_new(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse("bot_form.html", {
        "request": request,
        "bot": None,
    })


@router.post("/bots/new")
async def bot_form_submit(
    request: Request,
    student_name: str = Form(...),
    bot_name: str = Form(...),
    discord_token: str = Form(...),
    personality: str = Form(""),
    objective: str = Form(""),
    behavior_rules: str = Form(""),
) -> RedirectResponse:
    bot = await queries.create_bot(
        student_name=student_name,
        bot_name=bot_name,
        discord_token=discord_token,
        personality=personality,
        objective=objective,
        behavior_rules=behavior_rules,
    )
    fleet = request.app.state.fleet
    if fleet:
        await fleet.start_bot(bot)
    return RedirectResponse(url=f"/bots/{bot.id}", status_code=303)


@router.get("/bots/{bot_id}", response_class=HTMLResponse)
async def bot_detail(request: Request, bot_id: int) -> HTMLResponse:
    bot = await queries.get_bot(bot_id)
    if not bot:
        return HTMLResponse("<h1>Bot not found</h1>", status_code=404)
    stats = await queries.get_bot_stats(bot_id)
    grades = await queries.get_bot_grades(bot_id)
    conversations = await queries.get_bot_conversations(bot_id, limit=20)
    return TEMPLATES.TemplateResponse("bot_detail.html", {
        "request": request,
        "bot": bot,
        "stats": stats,
        "grades": grades,
        "conversations": conversations,
    })


@router.get("/bots/{bot_id}/edit", response_class=HTMLResponse)
async def bot_form_edit(request: Request, bot_id: int) -> HTMLResponse:
    bot = await queries.get_bot(bot_id)
    if not bot:
        return HTMLResponse("<h1>Bot not found</h1>", status_code=404)
    return TEMPLATES.TemplateResponse("bot_form.html", {
        "request": request,
        "bot": bot,
    })


@router.post("/bots/{bot_id}/edit")
async def bot_form_update(
    request: Request,
    bot_id: int,
    student_name: str = Form(...),
    bot_name: str = Form(...),
    discord_token: str = Form(...),
    personality: str = Form(""),
    objective: str = Form(""),
    behavior_rules: str = Form(""),
    is_active: str = Form("off"),
) -> RedirectResponse:
    await queries.update_bot(
        bot_id,
        student_name=student_name,
        bot_name=bot_name,
        discord_token=discord_token,
        personality=personality,
        objective=objective,
        behavior_rules=behavior_rules,
        is_active=1 if is_active == "on" else 0,
    )
    fleet = request.app.state.fleet
    if fleet:
        await fleet.reload_bot(bot_id)
    return RedirectResponse(url=f"/bots/{bot_id}", status_code=303)


@router.get("/grading", response_class=HTMLResponse)
async def grading_page(request: Request) -> HTMLResponse:
    grades = await queries.get_latest_grades()
    bots = {b.id: b for b in await queries.get_all_bots()}
    enriched = []
    for g in grades:
        bot = bots.get(g.bot_id)
        enriched.append({"grade": g, "bot": bot})
    return TEMPLATES.TemplateResponse("grading.html", {
        "request": request,
        "grades": enriched,
    })


@router.get("/messages", response_class=HTMLResponse)
async def messages_page(request: Request, bot_id: int | None = None) -> HTMLResponse:
    msgs = await queries.get_messages(limit=200, bot_id=bot_id)
    bots = await queries.get_all_bots()
    return TEMPLATES.TemplateResponse("messages.html", {
        "request": request,
        "messages": msgs,
        "bots": bots,
        "selected_bot_id": bot_id,
    })
