import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import flet as ft

from app.client import ApiClient, PresenceClient


class UIState(Enum):
    IDLE = "idle"
    LOGGING_IN = "logging_in"
    CONNECTED = "connected"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class Theme:
    PRIMARY = "#1E3A8A"
    PRIMARY_HOVER = "#1E40AF"
    SECONDARY = "#0F172A"
    SURFACE = "#EB0F172A"
    BORDER = "#2E93C5FD"
    FIELD_BG = "#26166D1F"
    FIELD_BORDER = "#4DCBD5F5"
    TEXT_PRIMARY = "#E2E8F0"
    TEXT_SECONDARY = "#94A3B8"
    TEXT_MUTED = "#BFE2E8F0"
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"

    BACKGROUND = ["#315DB6", "#061F5C", "#0032C9"]


class NotificationManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self.snack_bar = ft.SnackBar(
            content=ft.Text(""),
            action="Dismiss",
            duration=5000,
        )
        self.page.overlay.append(self.snack_bar)

    def show(self, message: str, severity: str = "info") -> None:
        colors = {
            "info": "#3B82F6",
            "success": Theme.SUCCESS,
            "warning": Theme.WARNING,
            "error": Theme.ERROR,
        }

        icon_map = {
            "info": "INFO",
            "success": "CHECK_CIRCLE",
            "warning": "WARNING",
            "error": "ERROR",
        }
        icon_name = icon_map.get(severity, "INFO")
        icon_value = getattr(ft.icons, icon_name, None)
        if icon_value is None:
            icon_value = getattr(ft.icons, "INFO", None)

        if icon_value is None:
            icon_control = ft.Text("i", color="#FFFFFF", size=18, weight=ft.FontWeight.BOLD)
        else:
            icon_control = ft.Icon(icon_value, color="#FFFFFF", size=20)

        self.snack_bar.content = ft.Row(
            [icon_control, ft.Text(message, color="#FFFFFF", size=14)],
            spacing=12,
        )

        self.snack_bar.bgcolor = colors.get(severity, "#3B82F6")
        self.snack_bar.open = True
        self.page.update()


class LoadingOverlay:
    def __init__(self):
        self.overlay = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(color=Theme.PRIMARY),
                    ft.Text("Loading...", color=Theme.TEXT_PRIMARY, size=16),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
            ),
            bgcolor="#DD000000",
            alignment=ft.Alignment(0, 0),
            visible=False,
            expand=True,
        )

    def show(self) -> None:
        self.overlay.visible = True

    def hide(self) -> None:
        self.overlay.visible = False


class UIComponents:
    @staticmethod
    def create_text_field(
        label: str,
        hint_text: str = "",
        password: bool = False,
        width: int = 360,
        **kwargs,
    ) -> ft.TextField:
        return ft.TextField(
            label=label,
            hint_text=hint_text,
            password=password,
            can_reveal_password=password,
            width=width,
            border_radius=12,
            filled=True,
            bgcolor=Theme.FIELD_BG,
            border_color=Theme.FIELD_BORDER,
            focused_border_color="#7DD3FC",
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY),
            **kwargs,
        )

    @staticmethod
    def create_button(
        text: str,
        on_click=None,
        primary: bool = True,
        width: int = 360,
        disabled: bool = False,
        **kwargs,
    ) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            text,
            on_click=on_click,
            disabled=disabled,
            style=ft.ButtonStyle(
                bgcolor=Theme.PRIMARY if primary else Theme.SECONDARY,
                color="#FFFFFF",
                padding=ft.padding.symmetric(18, 20),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
            width=width,
            **kwargs,
        )

    @staticmethod
    def create_card(
        title: str,
        content: ft.Control,
        min_height: int = 220,
        expand: bool = True,
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=Theme.TEXT_PRIMARY),
                    content,
                ],
                spacing=10,
                expand=True,
            ),
            padding=20,
            border_radius=16,
            bgcolor=Theme.SURFACE,
            border=ft.border.all(1, Theme.BORDER),
            shadow=[
                ft.BoxShadow(
                    blur_radius=30,
                    color="#330B1220",
                    offset=ft.Offset(0, 12),
                )
            ],
            height=min_height,
            expand=expand,
        )


class CRMAnalyticsUI:
    def __init__(self, page: ft.Page, api_url: str):
        self.page = page
        self.api_url = api_url
        self.api_client = ApiClient(api_url)
        self.presence_client: Optional[PresenceClient] = None
        self.notification = NotificationManager(page)
        self.loading = LoadingOverlay()

        self.current_state = UIState.IDLE
        self.current_user = None

        self._setup_page()
        self._create_widgets()
        self._setup_layout()

    def _setup_page(self) -> None:
        self.page.title = "CRM Analytics (LAN)"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = "adaptive"
        self.page.fonts = {
            "Sora": "https://fonts.gstatic.com/s/sora/v13/xMQbuFFYT72X1hY7vwbmrA.woff2",
            "IBM": "https://fonts.gstatic.com/s/ibmplexsans/v14/zYX-KVElMYYaJe8bpLHnCwDKhdzI.woff2",
        }
        self.page.theme = ft.Theme(font_family="IBM")
        self.page.on_disconnect = self._handle_page_disconnect

    def _create_widgets(self) -> None:
        self.status_text = ft.Text("Status: idle", color=Theme.TEXT_PRIMARY, size=13)
        self.user_text = ft.Text("User: -", color=Theme.TEXT_PRIMARY, size=13)

        self.log_view = ft.ListView(expand=True, spacing=6, auto_scroll=True)
        self.connected_list = ft.ListView(expand=True, spacing=4)
        self.connected_count = ft.Text(
            "Connected: 0",
            color=Theme.TEXT_PRIMARY,
            weight=ft.FontWeight.BOLD,
        )

        self.login_email = UIComponents.create_text_field(
            "Email",
            hint_text="you@company.com",
        )
        self.login_password = UIComponents.create_text_field(
            "Password",
            password=True,
        )
        self.login_btn = UIComponents.create_button(
            "Login",
            on_click=lambda e: self.page.run_task(self._login_async, e),
        )
        self.logout_btn = UIComponents.create_button(
            "Logout",
            on_click=lambda e: self.page.run_task(self._logout_async, e),
            primary=False,
            width=120,
            disabled=True,
        )

        self.create_email = UIComponents.create_text_field(
            "New user email",
            width=240,
        )
        self.create_name = UIComponents.create_text_field(
            "Name",
            width=200,
        )
        self.create_password = UIComponents.create_text_field(
            "Password",
            password=True,
            width=200,
        )
        self.create_role = ft.Dropdown(
            label="Role",
            options=[
                ft.dropdown.Option("user", "User"),
                ft.dropdown.Option("admin", "Admin"),
            ],
            value="user",
            width=160,
            border_color=Theme.FIELD_BORDER,
            focused_border_color="#7DD3FC",
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY),
        )
        self.create_btn = UIComponents.create_button(
            "Create user",
            on_click=lambda e: self.page.run_task(self._create_user_async, e),
            primary=False,
            width=140,
            disabled=True,
        )

        self.admin_section = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Create User",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.TEXT_PRIMARY,
                    ),
                    ft.Row(
                        [
                            self.create_email,
                            self.create_name,
                            self.create_password,
                            self.create_role,
                            self.create_btn,
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                ],
                spacing=12,
            ),
            padding=20,
            border_radius=16,
            bgcolor=Theme.SURFACE,
            border=ft.border.all(1, Theme.BORDER),
            visible=False,
        )

        self.logs_card = UIComponents.create_card("Activity Logs", self.log_view, min_height=280)
        self.logs_card.visible = False

        self.users_card = UIComponents.create_card(
            "Connected Users",
            ft.Column([self.connected_count, self.connected_list], expand=True),
            min_height=280,
        )

    def _setup_layout(self) -> None:
        login_card = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            "CRM",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=Theme.TEXT_PRIMARY,
                        ),
                        width=56,
                        height=56,
                        alignment=ft.Alignment(0, 0),
                        border_radius=14,
                        bgcolor="#401E3A8A",
                        border=ft.border.all(2, Theme.BORDER),
                    ),
                    ft.Text(
                        "CRM Analytics",
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=Theme.TEXT_SECONDARY,
                    ),
                    ft.Text(
                        "Welcome Back",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                        font_family="Sora",
                        color=Theme.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Sign in to access your workspace.",
                        size=13,
                        color=Theme.TEXT_MUTED,
                    ),
                    ft.Column(
                        [self.login_email, self.login_password, self.login_btn],
                        spacing=14,
                    ),
                ],
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=32,
            width=480,
            border_radius=24,
            bgcolor="#E0111827",
            border=ft.border.all(1, Theme.BORDER),
            shadow=[
                ft.BoxShadow(
                    blur_radius=50,
                    color="#4D020617",
                    offset=ft.Offset(0, 20),
                )
            ],
        )

        self.login_layer = ft.Container(
            content=login_card,
            alignment=ft.Alignment(0, 0),
            expand=True,
            visible=True,
        )

        status_bar = ft.Container(
            content=ft.Row(
                [
                    self.status_text,
                    self.user_text,
                    ft.Container(expand=True),
                    self.logout_btn,
                ],
                spacing=16,
            ),
            padding=ft.padding.only(bottom=8),
        )

        self.app_layer = ft.Container(
            content=ft.Column(
                [
                    status_bar,
                    self.admin_section,
                    ft.Row(
                        [self.users_card, self.logs_card],
                        spacing=16,
                        expand=True,
                    ),
                ],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.padding.only(left=24, right=24, top=24, bottom=24),
            expand=True,
            visible=False,
        )

        root = ft.Stack(
            [
                ft.Container(
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment(-1, -1),
                        end=ft.Alignment(1, 1),
                        colors=Theme.BACKGROUND,
                    ),
                ),
                self.login_layer,
                self.app_layer,
                self.loading.overlay,
            ],
            expand=True,
        )

        self.page.add(root)

    async def _add_log(self, message: str, level: str = "info") -> None:
        lower_message = message.lower()
        if lower_message.startswith("presence connecting") or lower_message.startswith(
            "presence connected"
        ):
            return
        if lower_message.startswith("presence connection"):
            return

        colors = {
            "info": Theme.TEXT_PRIMARY,
            "success": Theme.SUCCESS,
            "warning": Theme.WARNING,
            "error": Theme.ERROR,
        }

        timestamp = ft.Text(
            value=time.strftime("%H:%M:%S"),
            size=11,
            color=Theme.TEXT_SECONDARY,
            weight=ft.FontWeight.W_500,
        )

        message_text = ft.Text(
            message,
            color=colors.get(level, Theme.TEXT_PRIMARY),
            size=13,
        )

        self.log_view.controls.append(
            ft.Container(
                content=ft.Row([timestamp, message_text], spacing=10),
                padding=ft.padding.symmetric(vertical=4),
            )
        )
        self.page.update()

    async def _update_presence(self, users: list[dict]) -> None:
        self.connected_count.value = f"Connected: {len(users)}"
        icon_value = getattr(ft.icons, "PERSON", None)
        if icon_value is None:
            icon_value = getattr(ft.icons, "ACCOUNT_CIRCLE", None)
        self.connected_list.controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon_value, color=Theme.SUCCESS, size=16)
                        if icon_value
                        else ft.Text("•", color=Theme.SUCCESS, size=16),
                        ft.Text(
                            f"{user['name']} ({user['email']})",
                            color=Theme.TEXT_PRIMARY,
                            size=13,
                        ),
                        ft.Container(
                            content=ft.Text(
                                f"x{user['connections']}",
                                color=Theme.TEXT_PRIMARY,
                                size=11,
                            ),
                            bgcolor="#40059669",
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                            border_radius=8,
                        ),
                    ],
                    spacing=8,
                ),
                padding=ft.padding.symmetric(vertical=4),
            )
            for user in users
        ]
        self.page.update()

    async def _on_presence_disconnect(self) -> None:
        self.current_state = UIState.DISCONNECTED
        self.status_text.value = "Status: disconnected"
        self.status_text.color = Theme.ERROR
        await self._add_log("Presence connection lost", "error")
        self.notification.show("Connection to presence server lost", "error")
        self.page.update()

    async def _login_async(self, _: ft.ControlEvent | None = None) -> None:
        email = self.login_email.value.strip()
        password = self.login_password.value

        if not email or not password:
            self.notification.show("Email and password are required", "warning")
            await self._add_log("Login failed: Missing credentials", "warning")
            return

        self.current_state = UIState.LOGGING_IN
        self.status_text.value = "Status: logging in..."
        self.status_text.color = Theme.WARNING
        self.login_btn.disabled = True
        self.page.update()

        try:
            data = await self.api_client.login(email, password)
            user = data.get("user", {})
            self.current_user = user

            self.current_state = UIState.CONNECTED
            self.user_text.value = f"User: {user.get('name')} ({user.get('role')})"
            self.status_text.value = "Status: connected"
            self.status_text.color = Theme.SUCCESS

            is_admin = user.get("role") == "admin"
            self.admin_section.visible = is_admin
            self.create_btn.disabled = not is_admin
            self.logs_card.visible = is_admin

            self.logout_btn.disabled = False
            self.login_email.disabled = True
            self.login_password.disabled = True

            self.login_layer.visible = False
            self.app_layer.visible = True

            self.page.update()

            await self._add_log(f"Login successful as {user.get('name')}", "success")
            self.notification.show(f"Welcome back, {user.get('name')}!", "success")

            token = self.api_client.token
            if token:
                self.presence_client = PresenceClient(
                    self.api_url,
                    token,
                    self._update_presence,
                    self._add_log,
                    self._on_presence_disconnect,
                )
                await self.presence_client.start()

        except Exception as exc:
            self.current_state = UIState.ERROR
            self.status_text.value = "Status: error"
            self.status_text.color = Theme.ERROR
            self.login_btn.disabled = False

            error_msg = str(exc)
            await self._add_log(f"Login failed: {error_msg}", "error")
            self.notification.show(f"Login failed: {error_msg}", "error")
            self.page.update()

    async def _logout_async(self, _: ft.ControlEvent | None = None) -> None:
        if self.presence_client:
            await self.presence_client.stop()
            self.presence_client = None

        self.current_state = UIState.IDLE
        self.current_user = None

        self.logout_btn.disabled = True
        self.login_btn.disabled = False
        self.login_email.disabled = False
        self.login_password.disabled = False
        self.login_email.value = ""
        self.login_password.value = ""

        self.status_text.value = "Status: idle"
        self.status_text.color = Theme.TEXT_PRIMARY
        self.user_text.value = "User: -"

        self.admin_section.visible = False
        self.create_btn.disabled = True
        self.logs_card.visible = False

        self.login_layer.visible = True
        self.app_layer.visible = False

        await self._add_log("Logged out successfully", "info")
        self.notification.show("You have been logged out", "info")
        self.page.update()

    async def _create_user_async(self, _: ft.ControlEvent | None = None) -> None:
        email = self.create_email.value.strip()
        name = self.create_name.value.strip()
        password = self.create_password.value
        role = self.create_role.value or "user"

        if not email or not name or not password:
            self.notification.show("All fields are required", "warning")
            await self._add_log("User creation failed: Missing fields", "warning")
            return

        try:
            self.create_btn.disabled = True
            self.page.update()

            created = await self.api_client.create_user(email, name, password, role)

            self.create_email.value = ""
            self.create_name.value = ""
            self.create_password.value = ""
            self.create_role.value = "user"

            await self._add_log(f"User created: {created.get('email')}", "success")
            self.notification.show(
                f"User {created.get('email')} created successfully",
                "success",
            )

        except Exception as exc:
            error_msg = str(exc)
            await self._add_log(f"User creation failed: {error_msg}", "error")
            self.notification.show(f"Failed to create user: {error_msg}", "error")

        finally:
            self.create_btn.disabled = False
            self.page.update()

    def _handle_page_disconnect(self, _: ft.ControlEvent) -> None:
        try:
            self.page.run_task(self._cleanup_async)
        except Exception:
            pass

    async def _cleanup_async(self) -> None:
        if self.presence_client:
            await self.presence_client.stop()
            self.presence_client = None
        await self.api_client.close()


def main(page: ft.Page, api_url: str) -> None:
    CRMAnalyticsUI(page, api_url)
