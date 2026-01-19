import time
from typing import Optional

import flet as ft

from app.client import ApiClient, PresenceClient


def main(page: ft.Page, api_url: str) -> None:
    page.title = "CRM Analytics (LAN)"
    page.padding = 20
    page.scroll = "adaptive"

    api_client = ApiClient(api_url)
    presence_client: Optional[PresenceClient] = None

    status_text = ft.Text("Status: idle")
    user_text = ft.Text("User: -")

    log_view = ft.ListView(expand=True, spacing=6, auto_scroll=True)
    connected_list = ft.ListView(expand=True, spacing=4)
    connected_count = ft.Text("Connected: 0")

    login_email = ft.TextField(label="Email", width=320)
    login_password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=320,
    )
    login_btn = ft.ElevatedButton("Login")
    logout_btn = ft.ElevatedButton("Logout", disabled=True)

    create_email = ft.TextField(label="New user email", width=260)
    create_name = ft.TextField(label="Name", width=220)
    create_password = ft.TextField(
        label="Password",
        password=True,
        can_reveal_password=True,
        width=220,
    )
    create_role = ft.Dropdown(
        label="Role",
        options=[ft.dropdown.Option("user"), ft.dropdown.Option("admin")],
        value="user",
        width=160,
    )
    create_btn = ft.ElevatedButton("Create user", disabled=True)
    admin_section = ft.Column(
        [
            ft.Text("Create User", size=16, weight=ft.FontWeight.BOLD),
            ft.Row(
                [create_email, create_name, create_password, create_role, create_btn],
                spacing=10,
            ),
        ],
        visible=False,
    )
    async def add_log(message: str) -> None:
        timestamp = ft.Text(value=time.strftime("%H:%M:%S"), size=12)
        log_view.controls.append(ft.Row([timestamp, ft.Text(message)], spacing=8))
        page.update()

    async def update_presence(users: list[dict]) -> None:
        connected_count.value = f"Connected: {len(users)}"
        connected_list.controls = [
            ft.Text(f"{user['name']} ({user['email']}) x{user['connections']}")
            for user in users
        ]
        page.update()

    async def on_presence_disconnect() -> None:
        status_text.value = "Status: disconnected"
        page.update()

    async def login_async(_: ft.ControlEvent | None = None) -> None:
        nonlocal presence_client
        status_text.value = "Status: logging in..."
        page.update()

        email = login_email.value.strip()
        password = login_password.value
        if not email or not password:
            await add_log("Email and password are required.")
            status_text.value = "Status: error"
            page.update()
            return

        try:
            data = await api_client.login(email, password)
        except Exception as exc:
            await add_log(f"Login failed: {exc}")
            status_text.value = "Status: error"
            page.update()
            return

        user = data.get("user", {})
        user_text.value = f"User: {user.get('name')} ({user.get('role')})"
        status_text.value = "Status: connected"
        logout_btn.disabled = False
        login_btn.disabled = True
        login_email.disabled = True
        login_password.disabled = True
        is_admin = user.get("role") == "admin"
        admin_section.visible = is_admin
        create_btn.disabled = not is_admin
        page.update()

        await add_log("Login successful.")

        token = api_client.token
        if token:
            presence_client = PresenceClient(
                api_url,
                token,
                update_presence,
                add_log,
                on_presence_disconnect,
            )
            await presence_client.start()

    async def logout_async(_: ft.ControlEvent | None = None) -> None:
        nonlocal presence_client
        if presence_client:
            await presence_client.stop()
            presence_client = None
        logout_btn.disabled = True
        login_btn.disabled = False
        login_email.disabled = False
        login_password.disabled = False
        status_text.value = "Status: idle"
        user_text.value = "User: -"
        await add_log("Logged out.")
        page.update()

    login_btn.on_click = lambda e: page.run_task(login_async, e)
    logout_btn.on_click = lambda e: page.run_task(logout_async, e)
        admin_section.visible = False
        create_btn.disabled = True
        await add_log("Logged out.")
        page.update()

    async def create_user_async(_: ft.ControlEvent | None = None) -> None:
        email = create_email.value.strip()
        name = create_name.value.strip()
        password = create_password.value
        role = create_role.value or "user"
        if not email or not name or not password:
            await add_log("New user email, name, and password are required.")
            return
        try:
            created = await api_client.create_user(email, name, password, role)
        except Exception as exc:
            await add_log(f"Create user failed: {exc}")
            return
        create_email.value = ""
        create_name.value = ""
        create_password.value = ""
        create_role.value = "user"
        await add_log(f"User created: {created.get('email')}")
        page.update()

    login_btn.on_click = lambda e: page.run_task(login_async, e)
    logout_btn.on_click = lambda e: page.run_task(logout_async, e)
    create_btn.on_click = lambda e: page.run_task(create_user_async, e)

    async def cleanup_async() -> None:
        nonlocal presence_client
        if presence_client:
            await presence_client.stop()
            presence_client = None
        await api_client.close()

    def handle_page_disconnect(_: ft.ControlEvent) -> None:
        try:
            page.run_task(cleanup_async)
        except Exception:
            pass

    page.on_disconnect = handle_page_disconnect

    page.add(
        ft.Text("CRM Analytics", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([status_text, user_text, logout_btn], spacing=20),
        ft.Divider(),
        ft.Text("Login", size=16, weight=ft.FontWeight.BOLD),
        ft.Row([login_email, login_password, login_btn], spacing=10),
        admin_section,
        ft.Divider(),
        ft.Text("Connected Users", size=16, weight=ft.FontWeight.BOLD),
        connected_count,
        ft.Container(content=connected_list, height=180, border=ft.border.all(1)),
        ft.Divider(),
        ft.Text("Logs", size=16, weight=ft.FontWeight.BOLD),
        ft.Container(content=log_view, height=220, border=ft.border.all(1)),
    )
