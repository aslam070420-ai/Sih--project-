"""IVR dialog manager — the state machine that drives a call.

Public surface:

    mgr = DialogManager(session_dict)
    step = mgr.process_input(text="100 kilo tomato", dtmf=None)
    #   step.prompt      -> list[str]  sentences the TTS should speak
    #   step.intent      -> str
    #   step.action      -> dict | None (e.g. {'name':'createProduceListing', ...})
    #   step.ended       -> bool
    #   step.session     -> updated session dict

The manager is stateless between requests: it loads the session state
(``current_menu`` + ``conversation_state`` JSON), processes one input,
mutates the session, and returns. Persistence is handled by the caller
(the API blueprint) via ``ivr_session_*`` helpers in this module.
"""
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, Any, List

import db

from .i18n import PROMPTS, pick_prompt, WELCOME, MAIN_MENU, MORE_SERVICES_MENU, HELP_TEXT, ERRORS
from .intents import (recognize_intent, IntentResult,
                     LIST_PRODUCE, MARKET_PRICE, ORDER_STATUS, DELIVERY_STATUS,
                     BULK_ORDER, EARNINGS, HELP, LANGUAGE_CHANGE, MORE_SERVICES,
                     DEMAND_FORECAST, MY_LISTINGS, PAYMENT_STATUS, PROFILE_SUMMARY, AI_PRICE_RECOMMENDATION,
                     PLACE_ORDER,
                     CANCEL, CONFIRM, CHANGE, REPEAT, GO_BACK, MAIN_MENU as MAIN_MENU_INTENT,
                     UNKNOWN, RAW_NUMBER)
from .numbers import parse_quantity, parse_price, parse_grade, parse_harvest_offset, harvest_label_to_iso, HARVEST_LABEL_TA, HARVEST_LABEL_EN
from .services import (getFarmerByPhone, getUserByPhone, getFarmerProfile, authenticateIVRSession,
                      getMarketPrice, createProduceListing,
                      getFarmerOrders, getDeliveryStatus,
                      getBulkOpportunities, acceptBulkOpportunity,
                      getFarmerEarnings, getFarmerActiveListings, getDemandForecast,
                      getAIPriceRecommendation, previewIVROrder, createIVROrder, pretty_status)
from .products_dict import normalize_product
from .languages import resolve_language_selection, greeting, language_menu_prompt


# --------------------------------------------------------------------- Step result
@dataclass
class StepResult:
    prompt: List[str] = field(default_factory=list)
    intent: str = UNKNOWN
    intent_payload: Dict[str, Any] = field(default_factory=dict)
    action: Optional[Dict[str, Any]] = None     # backend action executed (or None)
    ended: bool = False
    new_menu: str = ""
    failure_count: int = 0
    session: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "intent": self.intent,
            "intent_payload": self.intent_payload,
            "action": self.action,
            "ended": self.ended,
            "new_menu": self.new_menu,
            "failure_count": self.failure_count,
        }


# --------------------------------------------------------------------- Session helpers
def new_session(caller_number: str, call_id: Optional[str] = None) -> dict:
    """Create a new IVR session row and return it as a dict."""
    token = uuid.uuid4().hex
    sid = db.execute(
        "INSERT INTO ivr_sessions (session_token, call_id, caller_number, language, "
        "current_menu, conversation_state, auth_status, status) "
        "VALUES (?,?,?,?,?,?,'unverified','active')",
        (token, call_id, caller_number, "ta", "language_select", "{}"))
    return load_session(sid)


def load_session(session_id: int) -> Optional[dict]:
    row = db.query("SELECT * FROM ivr_sessions WHERE id=?", (session_id,), one=True)
    if not row:
        return None
    s = dict(row)
    try:
        s["conversation_state"] = json.loads(s["conversation_state"] or "{}")
    except json.JSONDecodeError:
        s["conversation_state"] = {}
    return s


def load_session_by_token(token: str) -> Optional[dict]:
    row = db.query("SELECT * FROM ivr_sessions WHERE session_token=?", (token,), one=True)
    if not row:
        return None
    s = dict(row)
    try:
        s["conversation_state"] = json.loads(s["conversation_state"] or "{}")
    except json.JSONDecodeError:
        s["conversation_state"] = {}
    return s


def save_session(s: dict):
    state = json.dumps(s.get("conversation_state", {}), ensure_ascii=False)
    db.execute(
        "UPDATE ivr_sessions SET language=?, current_menu=?, current_intent=?, "
        "conversation_state=?, auth_status=?, failure_count=?, status=?, "
        "user_id=?, farmer_id=?, updated_at=datetime('now','localtime') WHERE id=?",
        (s.get("language", "ta"), s.get("current_menu", "main_menu"),
         s.get("current_intent"), state,
         s.get("auth_status", "unverified"), s.get("failure_count", 0),
         s.get("status", "active"),
         s.get("user_id"), s.get("farmer_id"),
         s["id"]))


def log_event(session_id: int, event_type: str, raw_input: str = None,
              recognized_text: str = None, intent: str = None,
              intent_payload: dict = None, response_text: str = None,
              backend_action: str = None, backend_result: dict = None,
              error: str = None):
    db.execute(
        "INSERT INTO ivr_events (session_id, event_type, raw_input, recognized_text, "
        "intent, intent_payload, response_text, backend_action, backend_result, error) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (session_id, event_type, raw_input, recognized_text, intent,
         json.dumps(intent_payload, ensure_ascii=False) if intent_payload else None,
         response_text,
         backend_action,
         json.dumps(backend_result, ensure_ascii=False) if backend_result else None,
         error))


def finalize_call_log(session: dict, intent: str, success: bool, had_error: bool,
                     duration_sec: int, transcript: list):
    # Counters live inside conversation_state JSON
    state = session.get("conversation_state", {})
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except json.JSONDecodeError:
            state = {}
    counters = state.get("_counters", {})
    db.execute(
        "INSERT INTO ivr_call_logs (session_id, caller_number, user_id, farmer_name, "
        "language, intent, success, had_error, duration_sec, listings_created, "
        "bulk_accepted, price_requests, order_requests, earnings_requests, "
        "start_time, end_time, transcript) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (session["id"], session.get("caller_number"), session.get("user_id"),
         session.get("_farmer_name") or state.get("_farmer_name"),
         session.get("language"), intent,
         1 if success else 0, 1 if had_error else 0, duration_sec,
         counters.get("listings_created", 0), counters.get("bulk_accepted", 0),
         counters.get("price_requests", 0), counters.get("order_requests", 0),
         counters.get("earnings_requests", 0),
         session.get("created_at"),
         datetime_str_now(),
         json.dumps(transcript, ensure_ascii=False)))


def datetime_str_now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------- DialogManager
class DialogManager:
    """Stateful wrapper around a single session dict.

    Each ``process_input`` call mutates ``self.session`` in place and
    returns a :class:`StepResult`. The caller is responsible for
    persisting the session via :func:`save_session`.
    """

    def __init__(self, session: dict):
        self.session = session
        self.lang = session.get("language", "ta")
        self.state = session.get("conversation_state", {})
        self.menu = session.get("current_menu", "language_select")

    # -- helpers -------------------------------------------------------
    def _say(self, *keys) -> List[str]:
        out = []
        for k in keys:
            if k in (WELCOME, MAIN_MENU, MORE_SERVICES_MENU, HELP_TEXT):
                out.extend(self._collection(k))
            else:
                txt = pick_prompt(k, self.lang, **self.state.get("fmt", {}))
                if txt:
                    out.append(txt)
        return out

    def _collection(self, coll) -> List[str]:
        if coll is WELCOME:
            return list(WELCOME[self.lang])
        if coll is MAIN_MENU:
            return list(MAIN_MENU[self.lang])
        if coll is MORE_SERVICES_MENU:
            return list(MORE_SERVICES_MENU[self.lang])
        if coll is HELP_TEXT:
            return list(HELP_TEXT[self.lang])
        return []

    def _reset_failure(self):
        self.session["failure_count"] = 0

    def _bump_failure(self) -> int:
        self.session["failure_count"] = self.session.get("failure_count", 0) + 1
        return self.session["failure_count"]

    def _failure_prompt(self) -> List[str]:
        n = self.session.get("failure_count", 0)
        if n <= 1:
            return [pick_prompt("speech_unclear_1", self.lang)]
        if n == 2:
            return [pick_prompt("speech_unclear_2", self.lang)]
        return [pick_prompt("speech_unclear_3", self.lang)]

    def _incr(self, key):
        # Persist counters inside conversation_state so they survive between
        # requests (the session dict itself is not persisted as a whole).
        self.state.setdefault("_counters", {})
        self.state["_counters"][key] = self.state["_counters"].get(key, 0) + 1

    def _fresh_dialog_state(self, seed: Optional[dict] = None) -> dict:
        """Return a new dialog-state dict that PRESERVES the call counters.

        Always use this instead of ``self.state = {...}`` from inside a
        handler, otherwise per-call counters (listings_created, price_requests,
        …) get lost between turns.
        """
        counters = self.state.get("_counters", {})
        farmer_name = self.state.get("_farmer_name")
        new_state = dict(seed or {})
        new_state["_counters"] = counters
        if farmer_name:
            new_state["_farmer_name"] = farmer_name
        return new_state

    # -- main entry ---------------------------------------------------
    def process_input(self, text: Optional[str] = None,
                     dtmf: Optional[str] = None) -> StepResult:
        # 1) try to recognize intent from text and/or DTMF
        ir = recognize_intent(text, self.lang, dtmf=dtmf, context=self.menu)
        result = StepResult(intent=ir.intent, intent_payload=ir.to_dict(),
                          session=self.session)
        # 2) dispatch by current menu
        if self.menu == "language_select":
            self._handle_language_select(ir, text, dtmf, result)
        else:
            self._handle_menu(ir, text, dtmf, result)

        # 3) persist state back into session dict so save_session stores it
        self.session["conversation_state"] = self.state
        self.session["language"] = self.lang
        self.session["current_intent"] = ir.intent if ir.intent != UNKNOWN else self.session.get("current_intent")

        result.new_menu = self.session.get("current_menu", "")
        result.failure_count = self.session.get("failure_count", 0)
        save_session(self.session)
        return result

    # -- language select ----------------------------------------------
    def _handle_language_select(self, ir, text, dtmf, result):
        """Select one of the supported Indian call languages.

        Two-digit DTMF codes (01..23) support the full language set. Spoken/native language names are
        also accepted by ``resolve_language_selection``.
        """
        selected = resolve_language_selection(dtmf=dtmf, text=text)
        if selected:
            self.lang = selected
            self.session["language"] = self.lang
            self._reset_failure()
            self.session["current_menu"] = "main_menu"
            self.menu = "main_menu"
            # Caller lookup happens after language is set so the welcome can be
            # personalised without changing any authentication behaviour.
            self._lookup_farmer()
            if self.session.get("user_id"):
                result.prompt = [
                    f"{greeting(self.lang)} {self.session.get('_farmer_name', '')}.",
                    *MAIN_MENU[self.lang],
                ]
            else:
                result.prompt = [
                    ERRORS["no_account"][self.lang],
                    *MAIN_MENU[self.lang],
                ]
            return

        self._bump_failure()
        result.prompt = [*self._failure_prompt(), *language_menu_prompt(self.lang)]

    # -- lookup farmer by phone --------------------------------------
    def _lookup_farmer(self):
        phone = self.session.get("caller_number", "")
        if not phone:
            return
        u = getUserByPhone(phone)
        if u:
            self.session["user_id"] = u["id"]
            if u.get("role") in ("farmer", "fpo"):
                self.session["farmer_id"] = u["id"]
                display = u.get("farm_name") or u.get("fpo_name") or u.get("name") or "Farmer"
            else:
                # Consumers and bulk buyers can now place marketplace orders by
                # IVR.  They intentionally do not receive a farmer_id, so all
                # farmer-only services remain protected exactly as before.
                self.session["farmer_id"] = None
                display = u.get("name") or "Caller"
            self.session["_farmer_name"] = display
            self.state.setdefault("_farmer_name", display)
            self.state["caller_role"] = u.get("role")
            self.session["auth_status"] = "verified"

    # -- main menu ----------------------------------------------------
    def _handle_menu(self, ir, text, dtmf, result):
        # Global control intents — work in any state
        if ir.intent == REPEAT:
            self._reset_failure()
            last_prompt = self.state.get("last_prompt")
            result.prompt = [last_prompt] if last_prompt else [pick_prompt("acknowledged", self.lang)]
            return
        if ir.intent == GO_BACK:
            self._reset_failure()
            prev = self.state.get("prev_menu", "main_menu")
            self.session["current_menu"] = prev
            self.menu = prev
            self.state["fmt"] = {}
            if prev == "main_menu":
                result.prompt = [pick_prompt("returning_to_main", self.lang), *MAIN_MENU[self.lang]]
            elif prev == "more_services":
                result.prompt = list(MORE_SERVICES_MENU[self.lang])
            else:
                result.prompt = self._say(prev)
            return
        if ir.intent == MAIN_MENU_INTENT:
            self._reset_failure()
            self.session["current_menu"] = "main_menu"
            # Preserve counters; only clear dialog-specific state
            for k in ("listing", "fmt", "bulk_opp", "order_purchase", "market_low",
                     "market_high", "market_suggested", "last_prompt", "prev_menu"):
                self.state.pop(k, None)
            result.prompt = [pick_prompt("returning_to_main", self.lang), *MAIN_MENU[self.lang]]
            return
        if ir.intent == CANCEL and self.menu != "main_menu":
            self._reset_failure()
            self.session["current_menu"] = "main_menu"
            for k in ("listing", "fmt", "bulk_opp", "order_purchase", "market_low",
                     "market_high", "market_suggested", "last_prompt", "prev_menu"):
                self.state.pop(k, None)
            result.prompt = [pick_prompt("list_cancelled", self.lang),
                            pick_prompt("returning_to_main", self.lang),
                            *MAIN_MENU[self.lang]]
            return

        # Dispatch on current menu
        handlers = {
            "main_menu": self._h_main_menu,
            "list_ask_crop": self._h_list_ask_crop,
            "list_ask_qty": self._h_list_ask_qty,
            "list_ask_price": self._h_list_ask_price,
            "list_ask_harvest": self._h_list_ask_harvest,
            "list_ask_grade": self._h_list_ask_grade,
            "list_confirm": self._h_list_confirm,
            "price_hint_offer": self._h_price_hint_offer,
            "price_hint_recommend": self._h_price_hint_recommend,
            "price_ask_crop": self._h_price_ask_crop,
            "price_report_done": self._h_main_menu,
            "order_report_done": self._h_main_menu,
            "delivery_report_done": self._h_main_menu,
            "bulk_confirm": self._h_bulk_confirm,
            "earnings_report_done": self._h_main_menu,
            "help_done": self._h_main_menu,
            "more_services": self._h_more_services,
            "forecast_ask_crop": self._h_forecast_ask_crop,
            "ai_price_ask_crop": self._h_ai_price_ask_crop,
            "order_place_ask_crop": self._h_order_place_ask_crop,
            "order_place_ask_qty": self._h_order_place_ask_qty,
            "order_place_ask_grade": self._h_order_place_ask_grade,
            "order_place_confirm": self._h_order_place_confirm,
        }
        handler = handlers.get(self.menu, self._h_main_menu)
        handler(ir, text, dtmf, result)

    # -- main menu handler -------------------------------------------
    def _h_main_menu(self, ir, text, dtmf, result):
        self._reset_failure()
        # If intent is still UNKNOWN, re-prompt main menu
        if ir.intent == UNKNOWN and ir.dtmf is None and not ir.raw_text:
            result.prompt = list(MAIN_MENU[self.lang])
            return
        if ir.intent == PLACE_ORDER or dtmf == "1":
            # Purchase is deliberately the first main-menu action in V8.
            self._start_order_purchase(result, ir)
        elif ir.intent == LIST_PRODUCE or dtmf == "2":
            # Fast-track the listing flow if the user already named a crop
            # and/or quantity in the same utterance ("I have 100 kilos of tomato").
            self.state = self._fresh_dialog_state({"listing": {}})
            self.session["current_menu"] = "list_ask_crop"
            if ir.product or ir.quantity:
                self._h_list_ask_crop(ir, text, dtmf, result)
            else:
                result.prompt = [pick_prompt("list_ask_crop", self.lang)]
        elif ir.intent == MARKET_PRICE or dtmf == "3":
            # Fast-track market price flow if user already named the crop.
            self.state = self._fresh_dialog_state()
            self.session["current_menu"] = "price_ask_crop"
            if ir.product:
                self._h_price_ask_crop(ir, text, dtmf, result)
            else:
                result.prompt = [pick_prompt("price_ask_crop", self.lang)]
        elif ir.intent == ORDER_STATUS or dtmf == "4":
            self._handle_order_status(result)
        elif ir.intent == DELIVERY_STATUS or dtmf == "5":
            self._handle_delivery_status(result)
        elif ir.intent == BULK_ORDER or dtmf == "6":
            self._handle_bulk_query(result)
        elif ir.intent == EARNINGS or dtmf == "7":
            self._handle_earnings(result)
        elif ir.intent == HELP or dtmf == "*":
            result.prompt = list(HELP_TEXT[self.lang])
            self.session["current_menu"] = "main_menu"
        elif ir.intent == LANGUAGE_CHANGE or dtmf == "8":
            self.session["current_menu"] = "language_select"
            self.menu = "language_select"
            result.prompt = language_menu_prompt(self.lang)
        elif ir.intent == MORE_SERVICES or dtmf == "9":
            self.session["current_menu"] = "more_services"
            self.menu = "more_services"
            result.prompt = list(MORE_SERVICES_MENU[self.lang])
        else:
            result.prompt = [ERRORS["invalid_choice"][self.lang], *MAIN_MENU[self.lang]]

    # -- extended services -------------------------------------------
    def _h_more_services(self, ir, text, dtmf, result):
        self._reset_failure()
        fid = self.session.get("farmer_id")
        if ir.intent == DEMAND_FORECAST or dtmf == "1":
            self.state["prev_menu"] = "more_services"
            self.session["current_menu"] = "forecast_ask_crop"
            result.prompt = [pick_prompt("forecast_ask_crop", self.lang)]
            return
        if ir.intent == MY_LISTINGS or dtmf == "2":
            if not fid:
                result.prompt = [ERRORS["no_account"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            else:
                data = getFarmerActiveListings(fid, 5)
                if not data["count"]:
                    result.prompt = [pick_prompt("listings_empty", self.lang), *MORE_SERVICES_MENU[self.lang]]
                else:
                    latest = data["items"][0]
                    result.prompt = [pick_prompt("listings_report", self.lang,
                        count=data["count"], qty=data["total_quantity_kg"],
                        crop=latest["crop"], grade=latest["grade"], price=latest["price_per_kg"]),
                        *MORE_SERVICES_MENU[self.lang]]
                result.action = {"name": "getFarmerActiveListings", "result": data}
            self.session["current_menu"] = "more_services"
            return
        if ir.intent == PAYMENT_STATUS or dtmf == "3":
            if not fid:
                result.prompt = [ERRORS["no_account"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            else:
                data = getFarmerEarnings(fid)
                result.prompt = [pick_prompt("payment_report", self.lang,
                    paid=int(data["paid"]), pending=int(data["pending"]), month=int(data["month"])),
                    *MORE_SERVICES_MENU[self.lang]]
                result.action = {"name": "getFarmerEarnings", "result": data}
            self.session["current_menu"] = "more_services"
            return
        if ir.intent == PROFILE_SUMMARY or dtmf == "4":
            if not fid:
                result.prompt = [ERRORS["no_account"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            else:
                data = getFarmerProfile(fid) or {}
                result.prompt = [pick_prompt("profile_report", self.lang,
                    name=data.get("name") or "Farmer", city=data.get("city") or "—",
                    farm=data.get("farm_name") or data.get("fpo_name") or "—",
                    crops=data.get("crops_grown") or "—", size=data.get("farm_size_acres") or 0),
                    *MORE_SERVICES_MENU[self.lang]]
                result.action = {"name": "getFarmerProfile", "result": data}
            self.session["current_menu"] = "more_services"
            return
        if ir.intent == AI_PRICE_RECOMMENDATION or dtmf == "5":
            self.state["prev_menu"] = "more_services"
            self.session["current_menu"] = "ai_price_ask_crop"
            result.prompt = [pick_prompt("ai_price_ask_crop", self.lang)]
            return
        if ir.intent == HELP or dtmf == "6":
            result.prompt = list(HELP_TEXT[self.lang])
            self.session["current_menu"] = "more_services"
            return
        if ir.intent == PLACE_ORDER:
            # Voice shortcut remains accepted here, but keypad ordering is
            # intentionally surfaced at main-menu option 1.
            self._start_order_purchase(result, ir)
            return
        if ir.intent == LANGUAGE_CHANGE or dtmf == "8":
            self.session["current_menu"] = "language_select"
            self.menu = "language_select"
            result.prompt = language_menu_prompt(self.lang)
            return
        result.prompt = [pick_prompt("more_services_invalid", self.lang), *MORE_SERVICES_MENU[self.lang]]

    # -- buy / place order --------------------------------------------
    def _start_order_purchase(self, result, ir=None):
        """Begin a real marketplace purchase from the IVR channel."""
        uid = self.session.get("user_id")
        if not uid:
            result.prompt = [ERRORS["no_account"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            self.session["current_menu"] = "more_services"
            return
        self.state = self._fresh_dialog_state({"order_purchase": {}})
        self.state["prev_menu"] = "more_services"
        self.session["current_menu"] = "order_place_ask_crop"
        if ir and ir.product:
            self._h_order_place_ask_crop(ir, ir.raw_text, ir.dtmf, result)
        else:
            result.prompt = [pick_prompt("order_place_ask_crop", self.lang)]

    def _h_order_place_ask_crop(self, ir, text, dtmf, result):
        if not ir.product:
            self._bump_failure()
            result.prompt = [pick_prompt("order_place_ask_crop", self.lang)]
            return
        self._reset_failure()
        self.state.setdefault("order_purchase", {})["crop"] = ir.product
        self.session["current_menu"] = "order_place_ask_qty"
        result.prompt = [pick_prompt("order_place_ask_qty", self.lang)]

    def _h_order_place_ask_qty(self, ir, text, dtmf, result):
        qty = ir.quantity
        if not qty or float(qty) <= 0:
            self._bump_failure()
            result.prompt = [pick_prompt("order_place_ask_qty", self.lang)]
            return
        self._reset_failure()
        self.state.setdefault("order_purchase", {})["quantity"] = float(qty)
        self.session["current_menu"] = "order_place_ask_grade"
        result.prompt = [pick_prompt("order_place_ask_grade", self.lang)]

    def _h_order_place_ask_grade(self, ir, text, dtmf, result):
        grade = ir.grade
        if not grade:
            self._bump_failure()
            result.prompt = [pick_prompt("order_place_ask_grade", self.lang)]
            return
        self._reset_failure()
        order = self.state.setdefault("order_purchase", {})
        order["grade"] = grade
        uid = self.session.get("user_id")
        try:
            quote = previewIVROrder(uid, order["crop"], order["quantity"], grade)
        except Exception as e:
            quote = {"ok": False, "error": str(e)}
        if not quote.get("ok"):
            available = float(quote.get("available_max_kg") or 0)
            if available > 0:
                result.prompt = [pick_prompt("order_place_stock_short", self.lang,
                                             available=int(available) if available.is_integer() else available)]
                self.session["current_menu"] = "order_place_ask_qty"
            else:
                result.prompt = [ERRORS["db_unavailable"][self.lang], *MORE_SERVICES_MENU[self.lang]]
                self.session["current_menu"] = "more_services"
            result.action = {"name": "previewIVROrder", "result": quote}
            return
        order["quote"] = quote
        self.session["current_menu"] = "order_place_confirm"
        qty = quote["quantity_kg"]
        qty_fmt = int(qty) if float(qty).is_integer() else qty
        result.prompt = [pick_prompt("order_place_quote", self.lang,
                                    qty=qty_fmt, crop=quote["crop"], grade=quote["grade"],
                                    price=quote["unit_price"], seller=quote["seller_name"],
                                    total=quote["total"])]
        result.action = {"name": "previewIVROrder", "result": quote}

    def _h_order_place_confirm(self, ir, text, dtmf, result):
        if ir.intent == CONFIRM or dtmf == "1":
            self._reset_failure()
            order = self.state.get("order_purchase") or {}
            quote = order.get("quote") or {}
            try:
                out = createIVROrder(self.session.get("user_id"), quote)
            except Exception as e:
                out = {"ok": False, "error": str(e)}
            if out.get("ok"):
                result.prompt = [pick_prompt("order_place_success", self.lang,
                                             code=out.get("order_code", out.get("id", "—")),
                                             total=out.get("total_amount", quote.get("total", 0))),
                                 *MORE_SERVICES_MENU[self.lang]]
                result.action = {"name": "createIVROrder", "result": out}
                self.session["current_menu"] = "more_services"
                self.state.pop("order_purchase", None)
                return
            result.prompt = [ERRORS["db_unavailable"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            result.action = {"name": "createIVROrder", "result": out}
            self.session["current_menu"] = "more_services"
            return
        if ir.intent in (CANCEL, CHANGE) or dtmf in ("2", "3"):
            self._reset_failure()
            self.state.pop("order_purchase", None)
            self.session["current_menu"] = "more_services"
            result.prompt = [pick_prompt("order_place_cancelled", self.lang), *MORE_SERVICES_MENU[self.lang]]
            return
        self._bump_failure()
        quote = (self.state.get("order_purchase") or {}).get("quote") or {}
        result.prompt = [pick_prompt("order_place_quote", self.lang,
                                    qty=quote.get("quantity_kg", "—"), crop=quote.get("crop", "—"),
                                    grade=quote.get("grade", "A"), price=quote.get("unit_price", "—"),
                                    seller=quote.get("seller_name", "—"), total=quote.get("total", "—"))]

    def _h_forecast_ask_crop(self, ir, text, dtmf, result):
        if not ir.product:
            self._bump_failure()
            result.prompt = [pick_prompt("forecast_ask_crop", self.lang)]
            return
        self._reset_failure()
        try:
            data = getDemandForecast(ir.product, 7)
            result.prompt = [pick_prompt("forecast_report", self.lang,
                days=7, crop=data["crop"], predicted=int(data["predicted_demand"]),
                current=int(data["current_demand"]), trend=data["trend"],
                confidence=int(round(float(data["confidence"]) * 100))),
                *MORE_SERVICES_MENU[self.lang]]
            result.action = {"name": "getDemandForecast", "result": data}
            self.session["current_menu"] = "more_services"
        except Exception as e:
            result.prompt = [ERRORS["db_unavailable"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            result.action = {"name": "getDemandForecast", "error": str(e)}
            self.session["current_menu"] = "more_services"

    def _h_ai_price_ask_crop(self, ir, text, dtmf, result):
        if not ir.product:
            self._bump_failure()
            result.prompt = [pick_prompt("ai_price_ask_crop", self.lang)]
            return
        fid = self.session.get("farmer_id")
        if not fid:
            result.prompt = [ERRORS["no_account"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            self.session["current_menu"] = "more_services"
            return
        self._reset_failure()
        try:
            data = getAIPriceRecommendation(fid, ir.product, "A", 100)
            result.prompt = [pick_prompt("ai_price_report", self.lang,
                crop=data["crop"], suggested=data["suggested_price"],
                mandi=data["mandi_price"], gain=data["earnings_gain_pct"]),
                *MORE_SERVICES_MENU[self.lang]]
            result.action = {"name": "getAIPriceRecommendation", "result": data}
            self.session["current_menu"] = "more_services"
        except Exception as e:
            result.prompt = [ERRORS["db_unavailable"][self.lang], *MORE_SERVICES_MENU[self.lang]]
            result.action = {"name": "getAIPriceRecommendation", "error": str(e)}
            self.session["current_menu"] = "more_services"

    # -- listing flow -------------------------------------------------
    def _h_list_ask_crop(self, ir, text, dtmf, result):
        if ir.intent == LIST_PRODUCE and ir.product:
            self._reset_failure()
            self.state["listing"]["crop"] = ir.product
            self.state["listing"]["quantity"] = ir.quantity
            self.state["listing"]["unit"] = ir.unit or "kg"
            self.session["current_menu"] = "list_ask_qty" if not ir.quantity else "list_ask_price"
            if ir.quantity:
                result.prompt = [pick_prompt("list_ask_price", self.lang)]
            else:
                result.prompt = [pick_prompt("list_ask_qty", self.lang)]
        elif ir.product:
            self._reset_failure()
            self.state["listing"]["crop"] = ir.product
            self.session["current_menu"] = "list_ask_qty"
            result.prompt = [pick_prompt("list_ask_qty", self.lang)]
        else:
            n = self._bump_failure()
            if n >= 3:
                # give DTMF crop menu
                crops = ["Tomato", "Onion", "Potato", "Banana", "Mango"]
                options = "; ".join(f"{crops[i]} {i+1}" for i in range(len(crops)))
                result.prompt = [pick_prompt("product_unknown", self.lang),
                               f"{options}.",
                               pick_prompt("speech_unclear_3", self.lang)]
            else:
                result.prompt = [pick_prompt("product_unknown", self.lang),
                               pick_prompt("list_ask_crop", self.lang)]

    def _h_list_ask_qty(self, ir, text, dtmf, result):
        qty = ir.quantity
        if qty:
            self._reset_failure()
            self.state["listing"]["quantity"] = qty
            self.state["listing"]["unit"] = ir.unit or "kg"
            self.session["current_menu"] = "list_ask_price"
            result.prompt = [pick_prompt("list_ask_price", self.lang)]
        else:
            n = self._bump_failure()
            if n >= 3:
                result.prompt = [pick_prompt("quantity_missing", self.lang),
                               pick_prompt("speech_unclear_3", self.lang)]
            else:
                result.prompt = [pick_prompt("quantity_missing", self.lang)]

    def _h_list_ask_price(self, ir, text, dtmf, result):
        price = ir.price
        if price is not None:
            self._reset_failure()
            self.state["listing"]["price"] = price
            self.session["current_menu"] = "list_ask_harvest"
            # AI price hint: fetch market range and offer comparison
            try:
                mp = getMarketPrice(self.state["listing"]["crop"], None)
                self.state["market_low"] = mp["low"]
                self.state["market_high"] = mp["high"]
                self.state["market_suggested"] = mp["suggested"]
                if price < mp["low"] * 0.95 or price > mp["high"] * 1.1:
                    self.session["current_menu"] = "price_hint_offer"
                    result.prompt = [pick_prompt("price_hint_offer", self.lang,
                                                price=int(price), low=int(mp["low"]),
                                                high=int(mp["high"]))]
                else:
                    result.prompt = [pick_prompt("list_ask_harvest", self.lang)]
            except Exception:
                result.prompt = [pick_prompt("list_ask_harvest", self.lang)]
        else:
            n = self._bump_failure()
            if n >= 3:
                result.prompt = [pick_prompt("price_missing", self.lang),
                               pick_prompt("speech_unclear_3", self.lang)]
            else:
                result.prompt = [pick_prompt("price_missing", self.lang)]

    def _replacement_price(self, ir, text, dtmf):
        """Return a newly-entered price while inside the AI correction flow.

        The recognizer treats keypad 1/2/3 as confirmation controls in these
        states, so a corrected numeric price must also be parsed explicitly.
        This keeps the value the farmer *last entered* as the source of truth.
        """
        if getattr(ir, "price", None) is not None:
            return float(ir.price)
        if text:
            parsed = parse_price(text)
            if parsed is not None:
                return float(parsed)
        raw_dtmf = str(dtmf).strip() if dtmf is not None else ""
        if raw_dtmf and raw_dtmf not in ("1", "2", "3"):
            parsed = parse_price(raw_dtmf)
            if parsed is not None:
                return float(parsed)
        return None

    def _accept_replacement_price(self, price, result):
        """Persist a corrected price and either accept it or re-offer guidance."""
        self.state["listing"]["price"] = float(price)
        low = self.state.get("market_low")
        high = self.state.get("market_high")
        if low is not None and high is not None and (price < low * 0.95 or price > high * 1.1):
            self.session["current_menu"] = "price_hint_offer"
            result.prompt = [pick_prompt(
                "price_hint_offer", self.lang, price=price, low=low, high=high)]
            return
        self._reset_failure()
        self.session["current_menu"] = "list_ask_harvest"
        result.prompt = [
            pick_prompt("price_updated", self.lang, price=price),
            pick_prompt("list_ask_harvest", self.lang),
        ]

    def _h_price_hint_offer(self, ir, text, dtmf, result):
        # A farmer may directly type/say a corrected price instead of pressing
        # 1 to hear the recommendation. Persist that new value immediately.
        replacement = self._replacement_price(ir, text, dtmf)
        if replacement is not None:
            self._accept_replacement_price(replacement, result)
            return

        if ir.intent == CONFIRM or dtmf == "1":
            self._reset_failure()
            self.session["current_menu"] = "price_hint_recommend"
            suggested = self.state.get("market_suggested", 0)
            result.prompt = [pick_prompt("price_hint_recommend", self.lang, suggested=suggested)]
        else:
            self._reset_failure()
            self.session["current_menu"] = "list_ask_harvest"
            # If the user spoke a harvest date while declining the hint,
            # capture it now so they don't have to repeat it.
            if ir.harvest_label:
                self.state["listing"]["harvest_label"] = ir.harvest_label
                self.state["listing"]["harvest_offset"] = ir.harvest_offset
                self.session["current_menu"] = "list_ask_grade"
                result.prompt = [pick_prompt("price_hint_skipped", self.lang),
                               pick_prompt("list_ask_grade", self.lang)]
            else:
                result.prompt = [pick_prompt("price_hint_skipped", self.lang),
                               pick_prompt("list_ask_harvest", self.lang)]

    def _h_price_hint_recommend(self, ir, text, dtmf, result):
        # Direct corrected-price entry is valid here too. Previously it was
        # ignored and the original rejected price survived into confirmation.
        replacement = self._replacement_price(ir, text, dtmf)
        if replacement is not None:
            self._accept_replacement_price(replacement, result)
            return

        if ir.intent == CONFIRM or dtmf == "1":
            accepted = float(self.state.get("market_suggested", self.state["listing"]["price"]))
            self.state["listing"]["price"] = accepted
            result.prompt = [pick_prompt("price_updated", self.lang, price=accepted)]
        else:
            result.prompt = []
        # either way proceed
        self._reset_failure()
        self.session["current_menu"] = "list_ask_harvest"
        # If the user spoke a harvest date while declining the recommendation,
        # capture it now so they don't have to repeat it.
        if ir.harvest_label:
            self.state["listing"]["harvest_label"] = ir.harvest_label
            self.state["listing"]["harvest_offset"] = ir.harvest_offset
            self.session["current_menu"] = "list_ask_grade"
            result.prompt.append(pick_prompt("list_ask_grade", self.lang))
        else:
            result.prompt.append(pick_prompt("list_ask_harvest", self.lang))

    def _h_list_ask_harvest(self, ir, text, dtmf, result):
        if ir.harvest_label:
            self._reset_failure()
            self.state["listing"]["harvest_label"] = ir.harvest_label
            self.state["listing"]["harvest_offset"] = ir.harvest_offset
            self.session["current_menu"] = "list_ask_grade"
            result.prompt = [pick_prompt("list_ask_grade", self.lang)]
        else:
            n = self._bump_failure()
            if n >= 3:
                # default to today
                self.state["listing"]["harvest_label"] = "today"
                self.state["listing"]["harvest_offset"] = 0
                self.session["current_menu"] = "list_ask_grade"
                result.prompt = [pick_prompt("list_ask_grade", self.lang)]
            else:
                result.prompt = [pick_prompt("list_ask_harvest", self.lang)]

    def _h_list_ask_grade(self, ir, text, dtmf, result):
        g = ir.grade
        if g is None and dtmf in ("1", "2", "3"):
            g = parse_grade(dtmf)
        if g:
            self._reset_failure()
            self.state["listing"]["grade"] = g
            self.session["current_menu"] = "list_confirm"
            harvest_label = self.state["listing"].get("harvest_label", "today")
            offset = self.state["listing"].get("harvest_offset")
            if offset is not None:
                if self.lang == "ta":
                    hl = HARVEST_LABEL_TA.get(harvest_label, harvest_label)
                else:
                    hl = HARVEST_LABEL_EN.get(harvest_label, harvest_label)
            else:
                hl = harvest_label
            self.state["fmt"] = dict(
                qty=int(self.state["listing"]["quantity"]),
                crop=self.state["listing"]["crop"],
                price=self.state["listing"]["price"],
                grade=g,
                harvest_label=hl,
            )
            summary = pick_prompt("list_summary", self.lang, **self.state["fmt"])
            confirm_opts = pick_prompt("list_confirm_options", self.lang)
            result.prompt = [summary, confirm_opts]
        else:
            n = self._bump_failure()
            if n >= 3:
                result.prompt = [pick_prompt("invalid_choice", self.lang),
                               pick_prompt("speech_unclear_3", self.lang)]
            else:
                result.prompt = [pick_prompt("list_ask_grade", self.lang)]

    def _h_list_confirm(self, ir, text, dtmf, result):
        if ir.intent == CONFIRM or dtmf == "1":
            self._reset_failure()
            farmer_id = self.session.get("farmer_id")
            if not farmer_id:
                # no account — fallback to admin so demo works even unauthed
                admin = db.query("SELECT id FROM users WHERE role='admin' LIMIT 1", one=True)
                farmer_id = admin["id"] if admin else 1
                self.session["farmer_id"] = farmer_id
                self.session["user_id"] = farmer_id
            try:
                lst = self.state["listing"]
                harvest_iso = harvest_label_to_iso(lst.get("harvest_label"),
                                                  lst.get("harvest_offset"))
                grade = lst.get("grade") or "A"
                out = createProduceListing(
                    farmer_id,
                    lst["crop"], float(lst["quantity"]),
                    float(lst["price"]), grade, harvest_iso)
                self._incr("listings_created")
                result.action = {"name": "createProduceListing", "result": out}
                result.prompt = [pick_prompt("list_success", self.lang),
                               pick_prompt("returning_to_main", self.lang),
                               *MAIN_MENU[self.lang]]
                self.session["current_menu"] = "main_menu"
                # Clear listing-specific state but PRESERVE counters
                self.state.pop("listing", None)
                self.state.pop("fmt", None)
                self.state.pop("market_low", None)
                self.state.pop("market_high", None)
                self.state.pop("market_suggested", None)
            except Exception as e:
                result.prompt = [ERRORS["db_unavailable"][self.lang]]
                result.action = {"name": "createProduceListing", "error": str(e)}
        elif ir.intent == CHANGE or dtmf == "2":
            self._reset_failure()
            self.session["current_menu"] = "list_ask_crop"
            self.state.pop("listing", None)
            self.state["listing"] = {}
            result.prompt = [pick_prompt("acknowledged", self.lang),
                           pick_prompt("list_ask_crop", self.lang)]
        else:  # cancel / 3
            self._reset_failure()
            self.session["current_menu"] = "main_menu"
            for k in ("listing", "fmt"):
                self.state.pop(k, None)
            result.prompt = [pick_prompt("list_cancelled", self.lang),
                           *MAIN_MENU[self.lang]]

    # -- market price flow --------------------------------------------
    def _h_price_ask_crop(self, ir, text, dtmf, result):
        if ir.product:
            self._reset_failure()
            try:
                mp = getMarketPrice(ir.product, None)
                self._incr("price_requests")
                result.prompt = [
                    pick_prompt("price_report", self.lang,
                                crop=mp["crop"], low=int(mp["low"]),
                                high=int(mp["high"]), avg=int(mp["avg"]),
                                updated=mp["updated"]),
                    pick_prompt("demo_note", self.lang) if mp["demo_data"] else
                    pick_prompt("cached_market_note", self.lang) if mp.get("status") == "cached" else
                    pick_prompt("official_market_note", self.lang,
                                market=mp.get("market") or "reported mandi",
                                state=mp.get("state") or "India"),
                    pick_prompt("returning_to_main", self.lang),
                    *MAIN_MENU[self.lang],
                ]
                result.prompt = [p for p in result.prompt if p]
                result.action = {"name": "getMarketPrice", "result": mp}
                self.session["current_menu"] = "main_menu"
            except Exception as e:
                result.prompt = [ERRORS["db_unavailable"][self.lang]]
                result.action = {"name": "getMarketPrice", "error": str(e)}
        else:
            n = self._bump_failure()
            if n >= 3:
                result.prompt = [pick_prompt("product_unknown", self.lang),
                               pick_prompt("speech_unclear_3", self.lang)]
            else:
                result.prompt = [pick_prompt("product_unknown", self.lang),
                               pick_prompt("price_ask_crop", self.lang)]

    # -- order status ------------------------------------------------
    def _handle_order_status(self, result):
        fid = self.session.get("farmer_id")
        if not fid:
            result.prompt = [ERRORS["no_account"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        orders = getFarmerOrders(fid, 5)
        self._incr("order_requests")
        if not orders:
            result.prompt = [ERRORS["no_orders"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        o = orders[0]
        status_txt = pretty_status(o["status"], self.lang)
        text = pick_prompt("order_latest", self.lang, code=o["order_code"], status=status_txt)
        extra = ""
        if o.get("buyer_name"):
            extra = (f"வாடிக்கையாளர்: {o['buyer_name']}." if self.lang == "ta"
                   else f"Buyer: {o['buyer_name']}.")
        more = pick_prompt("order_more", self.lang)
        result.prompt = [text, extra, more, *MAIN_MENU[self.lang]]
        result.prompt = [p for p in result.prompt if p]
        result.action = {"name": "getFarmerOrders", "result": orders}
        self.session["current_menu"] = "main_menu"

    # -- delivery status ---------------------------------------------
    def _handle_delivery_status(self, result):
        fid = self.session.get("farmer_id")
        if not fid:
            result.prompt = [ERRORS["no_account"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        dels = getDeliveryStatus(fid, 1)
        self._incr("order_requests")
        if not dels:
            result.prompt = [ERRORS["no_orders"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        d = dels[0]
        status_txt = pretty_status(d["status"], self.lang)
        extra = ""
        if d["status"] in ("picked_up", "in_transit"):
            eta = d["eta_minutes"]
            if self.lang == "ta":
                extra = f"எதிர்பார்க்கப்படும் நேரம் சுமார் {eta} நிமிடம். டிரைவர்: {d['driver_name']}."
            else:
                extra = f"Estimated time about {eta} minutes. Driver: {d['driver_name']}."
        elif d["status"] == "delivered":
            extra = (f"டெலிவரி முடிந்தது." if self.lang == "ta" else "Delivery completed.")
        text = pick_prompt("delivery_report", self.lang, code=d["order_code"], status=status_txt, extra=extra)
        result.prompt = [text, pick_prompt("returning_to_main", self.lang), *MAIN_MENU[self.lang]]
        result.prompt = [p for p in result.prompt if p]
        result.action = {"name": "getDeliveryStatus", "result": dels}
        self.session["current_menu"] = "main_menu"

    # -- bulk orders --------------------------------------------------
    def _handle_bulk_query(self, result):
        fid = self.session.get("farmer_id")
        if not fid:
            result.prompt = [ERRORS["no_account"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        opps = getBulkOpportunities(fid, 1)
        if not opps:
            result.prompt = [ERRORS["no_bulk"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        opp = opps[0]
        self.state["bulk_opp"] = opp
        text = pick_prompt("bulk_report", self.lang,
                          qty=int(opp["quantity_kg"]), crop=opp["crop"],
                          avail=int(opp["can_supply_kg"]))
        result.prompt = [text]
        result.action = {"name": "getBulkOpportunities", "result": opps}
        self.session["current_menu"] = "bulk_confirm"

    def _h_bulk_confirm(self, ir, text, dtmf, result):
        opp = self.state.get("bulk_opp")
        if not opp:
            self.session["current_menu"] = "main_menu"
            result.prompt = [*MAIN_MENU[self.lang]]
            return
        if ir.intent == CONFIRM or dtmf == "1":
            self._reset_failure()
            out = acceptBulkOpportunity(self.session["farmer_id"], opp["quote_id"],
                                        opp["can_supply_kg"])
            self._incr("bulk_accepted")
            result.action = {"name": "acceptBulkOpportunity", "result": out}
            if out.get("ok"):
                result.prompt = [pick_prompt("bulk_accept_ok", self.lang),
                               pick_prompt("returning_to_main", self.lang),
                               *MAIN_MENU[self.lang]]
            else:
                result.prompt = [ERRORS["db_unavailable"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
        else:
            self._reset_failure()
            result.prompt = [pick_prompt("bulk_declined", self.lang),
                           *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"

    # -- earnings -----------------------------------------------------
    def _handle_earnings(self, result):
        fid = self.session.get("farmer_id")
        if not fid:
            result.prompt = [ERRORS["no_account"][self.lang], *MAIN_MENU[self.lang]]
            self.session["current_menu"] = "main_menu"
            return
        self._incr("earnings_requests")
        e = getFarmerEarnings(fid)
        result.prompt = [pick_prompt("earnings_report", self.lang,
                                    today=int(e["today"]), week=int(e["week"]),
                                    month=int(e["month"]), paid=int(e["paid"]),
                                    pending=int(e["pending"])),
                       pick_prompt("returning_to_main", self.lang),
                       *MAIN_MENU[self.lang]]
        result.action = {"name": "getFarmerEarnings", "result": e}
        self.session["current_menu"] = "main_menu"
