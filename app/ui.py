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


class Section(Enum):
    DASHBOARD = "dashboard"
    ADMIN = "admin"


@dataclass
class Theme:
    # Primary Colors - Modern Blue Palette
    PRIMARY = "#2563EB"          # Bright modern blue
    PRIMARY_HOVER = "#1D4ED8"    # Deeper blue on hover
    PRIMARY_LIGHT = "#60A5FA"    # Light blue accent

    # Secondary Colors
    SECONDARY = "#0F172A"        # Deep slate
    SECONDARY_LIGHT = "#1E293B"  # Lighter slate

    # Surface Colors
    SURFACE = "#1E293B"          # Card background
    SURFACE_LIGHT = "#334155"    # Lighter surface
    SURFACE_HOVER = "#475569"    # Hover state

    # Border Colors
    BORDER = "#334155"           # Subtle border
    BORDER_LIGHT = "#475569"     # Lighter border

    # Field Colors
    FIELD_BG = "#0F172A"         # Dark field background
    FIELD_BORDER = "#334155"     # Field border
    FIELD_FOCUS = "#2563EB"      # Focus state

    # Text Colors
    TEXT_PRIMARY = "#F1F5F9"     # Bright white text
    TEXT_SECONDARY = "#94A3B8"   # Muted text
    TEXT_MUTED = "#64748B"       # Very muted text

    # Status Colors
    SUCCESS = "#10B981"          # Green
    SUCCESS_BG = "#064E3B"       # Dark green background
    WARNING = "#F59E0B"          # Orange
    WARNING_BG = "#78350F"       # Dark orange background
    ERROR = "#EF4444"            # Red
    ERROR_BG = "#7F1D1D"         # Dark red background
    INFO = "#3B82F6"             # Blue
    INFO_BG = "#1E3A8A"          # Dark blue background

    # Gradient Background
    BACKGROUND = ["#0F172A", "#1E293B", "#334155"]

    # Accent Colors
    ACCENT_PURPLE = "#8B5CF6"
    ACCENT_CYAN = "#06B6D4"
    ACCENT_PINK = "#EC4899"
    ACCENT_EMERALD = "#10B981"


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
            "info": Theme.INFO,
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
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=13),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=14),
            cursor_color=Theme.PRIMARY,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
            **kwargs,
        )

    @staticmethod
    def create_button(
        text: str,
        on_click=None,
        primary: bool = True,
        width: int = 360,
        disabled: bool = False,
        icon: str = None,
        **kwargs,
    ) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            text,
            icon=icon,
            on_click=on_click,
            disabled=disabled,
            bgcolor=Theme.PRIMARY if primary else Theme.SECONDARY_LIGHT,
            color="#FFFFFF",
            width=width,
            height=48,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
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
                    ft.Container(
                        content=ft.Text(
                            title,
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=Theme.TEXT_PRIMARY,
                        ),
                        padding=ft.padding.only(bottom=12),
                        border=ft.border.only(bottom=ft.BorderSide(1, Theme.BORDER)),
                    ),
                    content,
                ],
                spacing=16,
                expand=True,
            ),
            padding=24,
            border_radius=16,
            bgcolor=Theme.SURFACE,
            border=ft.border.all(1, Theme.BORDER),
            shadow=[
                ft.BoxShadow(
                    blur_radius=24,
                    color="#00000030",
                    offset=ft.Offset(0, 8),
                )
            ],
            height=min_height,
            expand=expand,
        )

    @staticmethod
    def create_kpi_card(title: str, value_text: ft.Text, icon: str = None, accent_color: str = None) -> ft.Container:
        """Create an enhanced KPI card with accent color"""
        if accent_color is None:
            accent_color = Theme.PRIMARY

        card_content = [
            ft.Text(
                title,
                size=14,
                color=Theme.TEXT_SECONDARY,
                weight=ft.FontWeight.W_500,
            ),
            ft.Container(height=12),
            value_text,
        ]

        return ft.Container(
            content=ft.Column(
                card_content,
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=ft.padding.all(24),
            border_radius=16,
            bgcolor=Theme.SURFACE,
            border=ft.border.all(2, accent_color),
            expand=True,
            shadow=[
                ft.BoxShadow(
                    blur_radius=20,
                    color="#00000020",
                    offset=ft.Offset(0, 4),
                )
            ],
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
        self.current_section = Section.DASHBOARD
        self.clients: list[dict] = []
        self.files: list[dict] = []
        self.reports: list[dict] = []
        self.selected_client_id: Optional[int] = None

        self._setup_page()
        self._create_widgets()
        self._setup_layout()

    def _setup_page(self) -> None:
        self.page.title = "CRM Analytics (LAN)"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = None
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
            "Sign In",
            on_click=lambda e: self.page.run_task(self._login_async, e),
        )
        self.logout_btn = UIComponents.create_button(
            "Sign Out",
            on_click=lambda e: self.page.run_task(self._logout_async, e),
            primary=False,
            width=140,
            disabled=True,
        )

        self.client_dropdown = ft.Dropdown(
            label="Select Client",
            options=[],
            value=None,
            width=200,
            border_color=Theme.FIELD_BORDER,
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=12),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=13),
            bgcolor=Theme.FIELD_BG,
            border_radius=10,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=10),
        )
        self.client_dropdown.on_change = self._handle_client_change
        self.refresh_dashboard_btn = UIComponents.create_button(
            "Refresh Data",
            on_click=lambda e: self.page.run_task(self._refresh_dashboard_async, e, True),
            primary=True,
            width=200,
            disabled=True,
        )

        # Selected client display
        self.selected_client_name = ft.Text(
            "Select a client",
            size=14,
            weight=ft.FontWeight.W_600,
            color=Theme.TEXT_PRIMARY,
        )

        # Dashboard title (will show client name)
        self.dashboard_title = ft.Text(
            "Dashboard",
            size=24,
            weight=ft.FontWeight.BOLD,
            color=Theme.TEXT_PRIMARY,
        )

        self.total_revenue_value = ft.Text(
            "-",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=Theme.ACCENT_EMERALD,
        )
        self.total_transactions_value = ft.Text(
            "-",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=Theme.ACCENT_CYAN,
        )
        self.revenue_today_value = ft.Text(
            "-",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=Theme.ACCENT_PURPLE,
        )

        self.metrics_row = ft.ResponsiveRow(
            [
                ft.Container(
                    content=UIComponents.create_kpi_card(
                        "Total Revenue",
                        self.total_revenue_value,
                        accent_color=Theme.ACCENT_EMERALD,
                    ),
                    col={"sm": 12, "md": 4, "lg": 4},
                ),
                ft.Container(
                    content=UIComponents.create_kpi_card(
                        "Transactions",
                        self.total_transactions_value,
                        accent_color=Theme.ACCENT_CYAN,
                    ),
                    col={"sm": 12, "md": 4, "lg": 4},
                ),
                ft.Container(
                    content=UIComponents.create_kpi_card(
                        "Revenue Today",
                        self.revenue_today_value,
                        accent_color=Theme.ACCENT_PURPLE,
                    ),
                    col={"sm": 12, "md": 4, "lg": 4},
                ),
            ],
            spacing=16,
            run_spacing=16,
        )
        self.data_sources_list = ft.ListView(expand=True, spacing=6)
        self.revenue_by_product_list = ft.ListView(expand=True, spacing=6)
        self.revenue_by_date_list = ft.ListView(expand=True, spacing=6)

        self.metrics_card = UIComponents.create_card(
            "Key Metrics",
            self.metrics_row,
            min_height=180,
            expand=False,
        )
        self.sources_card = UIComponents.create_card(
            "Data Sources",
            self.data_sources_list,
            min_height=240,
        )
        self.products_card = UIComponents.create_card(
            "Top Products",
            self.revenue_by_product_list,
            min_height=240,
        )
        self.dates_card = UIComponents.create_card(
            "Revenue by Date",
            self.revenue_by_date_list,
            min_height=240,
        )

        self.report_name = UIComponents.create_text_field("Report name", width=200)
        self.report_days = UIComponents.create_text_field("Last N days", width=120)
        self.report_days.value = "7"
        self.report_group_by = ft.Dropdown(
            label="Group by",
            options=[
                ft.dropdown.Option("product", "Product"),
                ft.dropdown.Option("region", "Region"),
                ft.dropdown.Option("salesperson", "Salesperson"),
                ft.dropdown.Option("date", "Date"),
            ],
            value="product",
            width=160,
            border_color=Theme.FIELD_BORDER,
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=13),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=14),
            bgcolor=Theme.FIELD_BG,
            border_radius=12,
        )
        self.report_metric = ft.Dropdown(
            label="Metric",
            options=[
                ft.dropdown.Option("revenue_sum", "Revenue Sum"),
                ft.dropdown.Option("quantity_sum", "Quantity Sum"),
                ft.dropdown.Option("rows_count", "Row Count"),
            ],
            value="revenue_sum",
            width=160,
            border_color=Theme.FIELD_BORDER,
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=13),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=14),
            bgcolor=Theme.FIELD_BG,
            border_radius=12,
        )
        self.report_file_dropdown = ft.Dropdown(
            label="Data source",
            options=[],
            value=None,
            width=220,
            border_color=Theme.FIELD_BORDER,
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=13),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=14),
            bgcolor=Theme.FIELD_BG,
            border_radius=12,
        )
        self.report_create_btn = UIComponents.create_button(
            "Create report",
            on_click=lambda e: self.page.run_task(self._create_report_async, e),
            primary=False,
            width=140,
            disabled=True,
        )
        self.report_select = ft.Dropdown(
            label="Saved reports",
            options=[],
            value=None,
            width=280,
            border_color=Theme.FIELD_BORDER,
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=13),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=14),
            bgcolor=Theme.FIELD_BG,
            border_radius=12,
        )
        self.report_run_btn = UIComponents.create_button(
            "Run report",
            on_click=lambda e: self.page.run_task(self._run_report_async, e),
            primary=False,
            width=120,
            disabled=True,
        )
        self.report_results_list = ft.ListView(expand=True, spacing=6)

        self.reports_card = UIComponents.create_card(
            "Reports",
            ft.Column(
                [
                    ft.Row(
                        [
                            self.report_file_dropdown,
                            self.report_name,
                            self.report_days,
                            self.report_group_by,
                            self.report_metric,
                            self.report_create_btn,
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                    ft.Row(
                        [
                            self.report_select,
                            self.report_run_btn,
                        ],
                        spacing=10,
                        wrap=True,
                    ),
                    self.report_results_list,
                ],
                spacing=12,
            ),
            min_height=300,
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
            focused_border_color=Theme.FIELD_FOCUS,
            label_style=ft.TextStyle(color=Theme.TEXT_SECONDARY, size=13),
            text_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=14),
            bgcolor=Theme.FIELD_BG,
            border_radius=12,
        )
        self.create_btn = UIComponents.create_button(
            "Create user",
            on_click=lambda e: self.page.run_task(self._create_user_async, e),
            primary=False,
            width=140,
            disabled=True,
        )

        self.client_name = UIComponents.create_text_field(
            "Client name",
            width=220,
        )
        self.client_code = UIComponents.create_text_field(
            "Client code",
            width=160,
        )
        self.client_description = UIComponents.create_text_field(
            "Description",
            width=260,
        )
        self.client_create_btn = UIComponents.create_button(
            "Create client",
            on_click=lambda e: self.page.run_task(self._create_client_async, e),
            primary=False,
            width=140,
            disabled=True,
        )

        self.assign_user_email = UIComponents.create_text_field(
            "User email",
            width=220,
        )
        self.assign_btn = UIComponents.create_button(
            "Assign to client",
            on_click=lambda e: self.page.run_task(self._assign_user_async, e),
            primary=False,
            width=150,
            disabled=True,
        )

        self.file_display_name = UIComponents.create_text_field(
            "File name",
            width=200,
        )
        self.file_path = UIComponents.create_text_field(
            "File path",
            width=260,
        )
        self.file_sheet = UIComponents.create_text_field(
            "Sheet (optional)",
            width=160,
        )
        self.file_has_header = ft.Checkbox(
            label="Has header row",
            value=True,
            label_style=ft.TextStyle(color=Theme.TEXT_PRIMARY, size=13),
            check_color=Theme.PRIMARY,
            active_color=Theme.PRIMARY,
        )
        self.map_date = UIComponents.create_text_field("Date column", width=140)
        self.map_product = UIComponents.create_text_field("Product column", width=140)
        self.map_quantity = UIComponents.create_text_field("Quantity column", width=140)
        self.map_revenue = UIComponents.create_text_field("Revenue column", width=140)
        self.map_region = UIComponents.create_text_field("Region column", width=140)
        self.map_salesperson = UIComponents.create_text_field("Salesperson column", width=160)
        self.map_date.value = "A"
        self.map_product.value = "B"
        self.map_quantity.value = "C"
        self.map_revenue.value = "D"
        self.map_region.value = "E"
        self.map_salesperson.value = "F"
        self.file_register_btn = UIComponents.create_button(
            "Register file",
            on_click=lambda e: self.page.run_task(self._register_file_async, e),
            primary=False,
            width=140,
            disabled=True,
        )

        self.logs_card = UIComponents.create_card("Activity Logs", self.log_view, min_height=280)
        self.logs_card.visible = False

        self.users_card = UIComponents.create_card(
            "Connected Users",
            ft.Column([self.connected_count, self.connected_list], expand=True),
            min_height=280,
        )

    def _create_nav_item(self, icon: str, label: str, section: Section) -> ft.Container:
        """Create a navigation item for the sidebar"""
        is_active = self.current_section == section

        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(icon, size=18),
                    ft.Text(
                        label,
                        size=14,
                        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.W_400,
                        color=Theme.TEXT_PRIMARY if is_active else Theme.TEXT_SECONDARY,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=10,
            bgcolor=Theme.PRIMARY if is_active else "transparent",
            on_click=lambda e, s=section: self.page.run_task(self._switch_section_async, s),
            on_hover=lambda e: self._on_nav_hover(e, section),
        )

    def _on_nav_hover(self, e: ft.ControlEvent, section: Section) -> None:
        """Handle hover effect on navigation items"""
        if self.current_section != section:
            e.control.bgcolor = Theme.SURFACE_HOVER if e.data == "true" else "transparent"
            e.control.update()

    async def _switch_section_async(self, section: Section) -> None:
        """Switch to a different section"""
        self.current_section = section
        self._update_navigation()
        self._update_content_visibility()
        self.page.update()

    def _update_navigation(self) -> None:
        """Update navigation items to reflect current section"""
        # Update Dashboard nav item
        is_dashboard_active = self.current_section == Section.DASHBOARD
        self.nav_dashboard.bgcolor = Theme.PRIMARY if is_dashboard_active else "transparent"
        self.nav_dashboard.content.controls[1].weight = ft.FontWeight.W_600 if is_dashboard_active else ft.FontWeight.W_400
        self.nav_dashboard.content.controls[1].color = Theme.TEXT_PRIMARY if is_dashboard_active else Theme.TEXT_SECONDARY

        # Update Admin nav item
        is_admin_active = self.current_section == Section.ADMIN
        self.nav_admin.bgcolor = Theme.PRIMARY if is_admin_active else "transparent"
        self.nav_admin.content.controls[1].weight = ft.FontWeight.W_600 if is_admin_active else ft.FontWeight.W_400
        self.nav_admin.content.controls[1].color = Theme.TEXT_PRIMARY if is_admin_active else Theme.TEXT_SECONDARY

    def _update_content_visibility(self) -> None:
        """Show/hide content based on current section"""
        self.dashboard_view.visible = self.current_section == Section.DASHBOARD
        self.admin_view.visible = self.current_section == Section.ADMIN

    def _setup_layout(self) -> None:
        login_card = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text(
                            "📊",
                            size=32,
                        ),
                        width=72,
                        height=72,
                        alignment=ft.Alignment(0, 0),
                        border_radius=20,
                        bgcolor=f"{Theme.PRIMARY}20",
                        border=ft.border.all(2, f"{Theme.PRIMARY}40"),
                    ),
                    ft.Text(
                        "CRM Analytics",
                        size=14,
                        weight=ft.FontWeight.W_500,
                        color=Theme.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Welcome Back",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        font_family="Sora",
                        color=Theme.TEXT_PRIMARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Sign in to access your analytics workspace",
                        size=14,
                        color=Theme.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=8),
                    ft.Column(
                        [self.login_email, self.login_password, self.login_btn],
                        spacing=16,
                    ),
                ],
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
            width=480,
            border_radius=24,
            bgcolor=Theme.SURFACE,
            border=ft.border.all(1, Theme.BORDER),
            shadow=[
                ft.BoxShadow(
                    blur_radius=40,
                    color="#00000040",
                    offset=ft.Offset(0, 16),
                )
            ],
        )

        self.login_layer = ft.Container(
            content=login_card,
            alignment=ft.Alignment(0, 0),
            expand=True,
            visible=True,
        )

        # Navigation items
        self.nav_dashboard = ft.Container(
            content=ft.Row(
                [
                    ft.Text("📊", size=18),
                    ft.Text(
                        "Dashboard",
                        size=14,
                        weight=ft.FontWeight.W_600,
                        color=Theme.TEXT_PRIMARY,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=10,
            bgcolor=Theme.PRIMARY,
            on_click=lambda e: self.page.run_task(self._switch_section_async, Section.DASHBOARD),
            on_hover=lambda e: self._on_nav_hover(e, Section.DASHBOARD),
        )

        self.nav_admin = ft.Container(
            content=ft.Row(
                [
                    ft.Text("⚙️", size=18),
                    ft.Text(
                        "Admin",
                        size=14,
                        weight=ft.FontWeight.W_400,
                        color=Theme.TEXT_SECONDARY,
                    ),
                ],
                spacing=12,
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=10,
            bgcolor="transparent",
            on_click=lambda e: self.page.run_task(self._switch_section_async, Section.ADMIN),
            on_hover=lambda e: self._on_nav_hover(e, Section.ADMIN),
            visible=False,  # Hidden by default, shown for admins
        )

        # Sidebar
        sidebar = ft.Container(
            content=ft.Column(
                [
                    # Client Selector at top
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "CLIENT",
                                    size=11,
                                    color=Theme.TEXT_MUTED,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(height=8),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Container(
                                                content=ft.Text("🏢", size=20),
                                                width=36,
                                                height=36,
                                                alignment=ft.Alignment(0, 0),
                                                border_radius=8,
                                                bgcolor=f"{Theme.PRIMARY}30",
                                            ),
                                            self.selected_client_name,
                                        ],
                                        spacing=10,
                                    ),
                                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                                    border_radius=10,
                                    bgcolor=Theme.FIELD_BG,
                                    border=ft.border.all(1, Theme.BORDER),
                                ),
                                ft.Container(height=8),
                                self.client_dropdown,
                                ft.Container(height=4),
                                self.refresh_dashboard_btn,
                            ],
                            spacing=0,
                        ),
                        padding=ft.padding.only(bottom=20),
                    ),
                    ft.Divider(color=Theme.BORDER, height=1),
                    ft.Container(height=16),
                    # Navigation
                    ft.Text(
                        "MENU",
                        size=11,
                        color=Theme.TEXT_MUTED,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(height=8),
                    self.nav_dashboard,
                    self.nav_admin,
                    ft.Container(expand=True),
                    # User info at bottom
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Divider(color=Theme.BORDER, height=1),
                                ft.Container(height=12),
                                ft.Row(
                                    [
                                        ft.Text("●", color=Theme.SUCCESS, size=10),
                                        self.status_text,
                                    ],
                                    spacing=6,
                                ),
                                ft.Row(
                                    [
                                        ft.Text("👤", size=12),
                                        self.user_text,
                                    ],
                                    spacing=6,
                                ),
                                ft.Container(height=8),
                                self.logout_btn,
                            ],
                            spacing=4,
                        ),
                    ),
                ],
                spacing=4,
            ),
            width=240,
            padding=20,
            bgcolor=Theme.SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, Theme.BORDER)),
        )

        # Dashboard View
        self.dashboard_view = ft.Container(
            content=ft.Column(
                [
                    self.dashboard_title,
                    ft.Container(height=16),
                    self.metrics_card,
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=self.sources_card,
                                col={"sm": 12, "md": 4, "lg": 4},
                            ),
                            ft.Container(
                                content=self.products_card,
                                col={"sm": 12, "md": 4, "lg": 4},
                            ),
                            ft.Container(
                                content=self.dates_card,
                                col={"sm": 12, "md": 4, "lg": 4},
                            ),
                        ],
                        spacing=16,
                        run_spacing=16,
                    ),
                    self.reports_card,
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=self.users_card,
                                col={"sm": 12, "md": 6, "lg": 6},
                            ),
                            ft.Container(
                                content=self.logs_card,
                                col={"sm": 12, "md": 6, "lg": 6},
                            ),
                        ],
                        spacing=16,
                        run_spacing=16,
                    ),
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
            visible=True,
        )

        # Admin View
        self.admin_view = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Admin Panel",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=Theme.TEXT_PRIMARY,
                    ),
                    ft.Container(height=16),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                content=UIComponents.create_card(
                                    "Create User",
                                    ft.Column(
                                        [
                                            ft.Row([self.create_email, self.create_name], spacing=12, wrap=True),
                                            ft.Row([self.create_password, self.create_role], spacing=12, wrap=True),
                                            self.create_btn,
                                        ],
                                        spacing=12,
                                    ),
                                    min_height=220,
                                    expand=True,
                                ),
                                col={"sm": 12, "md": 6, "lg": 6},
                            ),
                            ft.Container(
                                content=UIComponents.create_card(
                                    "Create Client",
                                    ft.Column(
                                        [
                                            self.client_name,
                                            ft.Row([self.client_code, self.client_description], spacing=12, wrap=True),
                                            self.client_create_btn,
                                        ],
                                        spacing=12,
                                    ),
                                    min_height=220,
                                    expand=True,
                                ),
                                col={"sm": 12, "md": 6, "lg": 6},
                            ),
                        ],
                        spacing=16,
                        run_spacing=16,
                    ),
                    UIComponents.create_card(
                        "Assign User to Client",
                        ft.Row(
                            [
                                self.assign_user_email,
                                self.assign_btn,
                            ],
                            spacing=12,
                            wrap=True,
                        ),
                        min_height=140,
                        expand=False,
                    ),
                    UIComponents.create_card(
                        "Register Excel File",
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        self.file_display_name,
                                        self.file_path,
                                        self.file_sheet,
                                    ],
                                    spacing=12,
                                    wrap=True,
                                ),
                                ft.Row(
                                    [
                                        self.file_has_header,
                                        ft.Container(expand=True),
                                    ],
                                ),
                                ft.Text(
                                    "Column Mappings",
                                    size=14,
                                    weight=ft.FontWeight.W_500,
                                    color=Theme.TEXT_SECONDARY,
                                ),
                                ft.Row(
                                    [
                                        self.map_date,
                                        self.map_product,
                                        self.map_quantity,
                                        self.map_revenue,
                                        self.map_region,
                                        self.map_salesperson,
                                    ],
                                    spacing=12,
                                    wrap=True,
                                ),
                                self.file_register_btn,
                            ],
                            spacing=12,
                        ),
                        min_height=300,
                        expand=False,
                    ),
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
            visible=False,
        )

        # Main content area
        main_content = ft.Container(
            content=ft.Stack(
                [
                    self.dashboard_view,
                    self.admin_view,
                ],
                expand=True,
            ),
            padding=ft.padding.all(28),
            expand=True,
        )

        # App layer with sidebar
        self.app_layer = ft.Container(
            content=ft.Row(
                [
                    sidebar,
                    main_content,
                ],
                spacing=0,
                expand=True,
            ),
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

    def _handle_client_change(self, e: ft.ControlEvent) -> None:
        """Handle client dropdown change event"""
        self.page.run_task(self._on_client_change_async, e)

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
        self.connected_count.value = f"Connected Users: {len(users)}"

        self.connected_list.controls = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text("👤", size=16),
                            width=36,
                            height=36,
                            bgcolor=f"{Theme.SUCCESS}20",
                            border_radius=10,
                            alignment=ft.Alignment(0, 0),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    user['name'],
                                    color=Theme.TEXT_PRIMARY,
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                ),
                                ft.Text(
                                    user['email'],
                                    color=Theme.TEXT_SECONDARY,
                                    size=11,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.Container(expand=True),
                        ft.Container(
                            content=ft.Text(
                                f"×{user['connections']}",
                                color=Theme.TEXT_PRIMARY,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                            ),
                            bgcolor=Theme.SECONDARY_LIGHT,
                            padding=ft.padding.symmetric(horizontal=10, vertical=4),
                            border_radius=10,
                        ),
                    ],
                    spacing=12,
                ),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                bgcolor=Theme.FIELD_BG,
                border_radius=12,
                border=ft.border.all(1, Theme.BORDER),
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

    async def _load_clients_async(self) -> None:
        try:
            if self.current_user and self.current_user.get("role") == "admin":
                clients = await self.api_client.list_clients()
            else:
                clients = await self.api_client.list_my_clients()
        except Exception as exc:
            await self._add_log(f"Failed to load clients: {exc}", "error")
            self.notification.show("Failed to load clients", "error")
            return

        self.clients = clients
        self.client_dropdown.options = [
            ft.dropdown.Option(str(client["id"]), client["name"]) for client in clients
        ]

        if clients:
            first_client = clients[0]
            self.client_dropdown.value = str(first_client["id"])
            self.selected_client_id = first_client["id"]
            self.selected_client_name.value = first_client.get("name", "Unknown")
            self.dashboard_title.value = f"Dashboard - {first_client.get('name', 'Unknown')}"
            self.refresh_dashboard_btn.disabled = False
            self.page.update()
            await self._load_files_async()
            await self._load_reports_async()
            await self._refresh_dashboard_async(force=True)
        else:
            self.client_dropdown.value = None
            self.selected_client_id = None
            self.selected_client_name.value = "No clients available"
            self.dashboard_title.value = "Dashboard"
            self.refresh_dashboard_btn.disabled = True
            self.files = []
            self.reports = []
            self.report_file_dropdown.options = []
            self.report_select.options = []
            self.report_create_btn.disabled = True
            self.report_run_btn.disabled = True
            self.page.update()

    async def _on_client_change_async(self, e: ft.ControlEvent | None = None) -> None:
        # Always use the dropdown's current value (more reliable than e.data)
        new_value = self.client_dropdown.value

        if not new_value:
            self.selected_client_id = None
            self.refresh_dashboard_btn.disabled = True
            self._clear_dashboard_data()
            self.page.update()
            return

        try:
            new_client_id = int(new_value)
        except (ValueError, TypeError):
            self.selected_client_id = None
            self.refresh_dashboard_btn.disabled = True
            self._clear_dashboard_data()
            self.page.update()
            return

        # Only reload if client actually changed
        if new_client_id == self.selected_client_id:
            return

        self.selected_client_id = new_client_id
        self.refresh_dashboard_btn.disabled = True
        self.page.update()

        # Find client name for notification
        client_name = "Unknown"
        for c in self.clients:
            if c.get("id") == new_client_id:
                client_name = c.get("name", "Unknown")
                break

        # Update client name displays
        self.selected_client_name.value = client_name
        self.dashboard_title.value = f"Dashboard - {client_name}"
        self.page.update()

        await self._add_log(f"Switching to client: {client_name}", "info")

        await self._load_files_async()
        await self._load_reports_async()
        await self._refresh_dashboard_async(None, force=True)

        self.notification.show(f"Loaded data for {client_name}", "success")

    def _clear_dashboard_data(self) -> None:
        """Clear all dashboard data when no client is selected"""
        self.selected_client_name.value = "Select a client"
        self.dashboard_title.value = "Dashboard"
        self.total_revenue_value.value = "-"
        self.total_transactions_value.value = "-"
        self.revenue_today_value.value = "-"
        self.data_sources_list.controls = []
        self.revenue_by_product_list.controls = []
        self.revenue_by_date_list.controls = []
        self.files = []
        self.reports = []
        self.report_file_dropdown.options = []
        self.report_file_dropdown.value = None
        self.report_select.options = []
        self.report_select.value = None
        self.report_results_list.controls = []
        self.report_create_btn.disabled = True
        self.report_run_btn.disabled = True

    async def _load_files_async(self) -> None:
        if not self.selected_client_id:
            return
        try:
            files = await self.api_client.list_files(self.selected_client_id)
        except Exception as exc:
            await self._add_log(f"Failed to load files: {exc}", "error")
            self.notification.show("Failed to load files", "error")
            return
        self.files = files
        self.report_file_dropdown.options = [
            ft.dropdown.Option(str(file_row["id"]), file_row["display_name"])
            for file_row in files
        ]
        if files:
            self.report_file_dropdown.value = str(files[0]["id"])
            self.report_create_btn.disabled = False
        else:
            self.report_file_dropdown.value = None
            self.report_create_btn.disabled = True
        self.page.update()

    async def _load_reports_async(self) -> None:
        if not self.selected_client_id:
            return
        try:
            reports = await self.api_client.list_reports(self.selected_client_id)
        except Exception as exc:
            await self._add_log(f"Failed to load reports: {exc}", "error")
            self.notification.show("Failed to load reports", "error")
            return
        self.reports = reports
        self.report_select.options = [
            ft.dropdown.Option(str(report["id"]), report["name"]) for report in reports
        ]
        self.report_results_list.controls = []
        if reports:
            self.report_select.value = str(reports[0]["id"])
            self.report_run_btn.disabled = False
        else:
            self.report_select.value = None
            self.report_run_btn.disabled = True
        self.page.update()

    async def _refresh_dashboard_async(
        self, _: ft.ControlEvent | None = None, force: bool = False
    ) -> None:
        if not self.selected_client_id:
            self.notification.show("Please select a client first", "warning")
            return

        # Disable refresh button while loading
        self.refresh_dashboard_btn.disabled = True
        self.page.update()

        try:
            dashboard = await self.api_client.get_dashboard(
                self.selected_client_id, force=force
            )
        except Exception as exc:
            await self._add_log(f"Failed to load dashboard: {exc}", "error")
            self.notification.show("Failed to load dashboard", "error")
            self.refresh_dashboard_btn.disabled = False
            self.page.update()
            return

        try:
            total_revenue = float(dashboard.get("total_revenue") or 0)
        revenue_today = float(dashboard.get("revenue_today") or 0)
        total_transactions = int(dashboard.get("total_transactions") or 0)
        self.total_revenue_value.value = f"${total_revenue:,.2f}"
        self.total_transactions_value.value = str(total_transactions)
        self.revenue_today_value.value = f"${revenue_today:,.2f}"

        self.data_sources_list.controls = []
        for source in dashboard.get("data_sources", []):
            self.data_sources_list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text("📊", size=16),
                            ft.Text(
                                source.get("display_name", "-"),
                                color=Theme.TEXT_PRIMARY,
                                size=13,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Text(
                                    f"{source.get('row_count', 0)} rows",
                                    color=Theme.TEXT_PRIMARY,
                                    size=11,
                                    weight=ft.FontWeight.W_500,
                                ),
                                bgcolor=Theme.SECONDARY_LIGHT,
                                padding=ft.padding.symmetric(horizontal=10, vertical=4),
                                border_radius=8,
                            ),
                        ],
                        spacing=12,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                    border_radius=8,
                    bgcolor=Theme.FIELD_BG,
                )
            )

        self.revenue_by_product_list.controls = []
        max_revenue = max([float(item.get("value") or 0) for item in dashboard.get("revenue_by_product", [])], default=1)
        for idx, item in enumerate(dashboard.get("revenue_by_product", [])):
            value = float(item.get("value") or 0)
            percentage = (value / max_revenue) * 100 if max_revenue > 0 else 0

            # Color gradient based on position
            bar_color = [Theme.ACCENT_EMERALD, Theme.ACCENT_CYAN, Theme.ACCENT_PURPLE][idx % 3]

            self.revenue_by_product_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        item.get("label", "-"),
                                        color=Theme.TEXT_PRIMARY,
                                        size=13,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Container(expand=True),
                                    ft.Text(
                                        f"${value:,.2f}",
                                        color=bar_color,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Container(
                                content=ft.Container(
                                    bgcolor=bar_color,
                                    height=4,
                                    border_radius=2,
                                ),
                                width=f"{percentage}%",
                                bgcolor=Theme.FIELD_BG,
                                height=4,
                                border_radius=2,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=8),
                )
            )

        self.revenue_by_date_list.controls = []
        date_items = dashboard.get("revenue_by_date", [])[-10:]
        max_date_revenue = max([float(item.get("value") or 0) for item in date_items], default=1)

        for item in date_items:
            value = float(item.get("value") or 0)
            percentage = (value / max_date_revenue) * 100 if max_date_revenue > 0 else 0

            self.revenue_by_date_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("📅", size=14),
                                    ft.Text(
                                        item.get("label", "-"),
                                        color=Theme.TEXT_PRIMARY,
                                        size=13,
                                    ),
                                    ft.Container(expand=True),
                                    ft.Text(
                                        f"${value:,.2f}",
                                        color=Theme.ACCENT_EMERALD,
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Container(
                                content=ft.Container(
                                    bgcolor=Theme.ACCENT_PURPLE,
                                    height=3,
                                    border_radius=2,
                                ),
                                width=f"{percentage}%",
                                bgcolor=Theme.FIELD_BG,
                                height=3,
                                border_radius=2,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=ft.padding.symmetric(horizontal=8, vertical=6),
                )
            )
        except Exception as exc:
            await self._add_log(f"Error processing dashboard data: {exc}", "error")
            self.notification.show("Error displaying dashboard data", "error")
        finally:
            # Always re-enable refresh button
            self.refresh_dashboard_btn.disabled = False
            self.page.update()

    async def _create_client_async(self, _: ft.ControlEvent | None = None) -> None:
        name = (self.client_name.value or "").strip()
        code = (self.client_code.value or "").strip()
        description = (self.client_description.value or "").strip() or None

        # Validation
        if not name or not code:
            self.notification.show("Client name and code are required", "warning")
            await self._add_log("Client creation failed: Missing fields", "warning")
            return

        if len(name) < 2:
            self.notification.show("Client name must be at least 2 characters", "warning")
            await self._add_log("Client creation failed: Name too short", "warning")
            return

        if len(code) < 2:
            self.notification.show("Client code must be at least 2 characters", "warning")
            await self._add_log("Client creation failed: Code too short", "warning")
            return
        try:
            self.client_create_btn.disabled = True
            self.page.update()
            created = await self.api_client.create_client(name, code, description)
            self.client_name.value = ""
            self.client_code.value = ""
            self.client_description.value = ""
            await self._add_log(f"Client created: {created.get('name')}", "success")
            self.notification.show("Client created", "success")
            await self._load_clients_async()
        except Exception as exc:
            await self._add_log(f"Client creation failed: {exc}", "error")
            self.notification.show("Failed to create client", "error")
        finally:
            self.client_create_btn.disabled = False
            self.page.update()

    async def _assign_user_async(self, _: ft.ControlEvent | None = None) -> None:
        if not self.selected_client_id:
            self.notification.show("Please select a client first", "warning")
            await self._add_log("User assignment failed: No client selected", "warning")
            return

        email = (self.assign_user_email.value or "").strip()
        if not email:
            self.notification.show("User email is required", "warning")
            await self._add_log("User assignment failed: Missing email", "warning")
            return

        if "@" not in email:
            self.notification.show("Please enter a valid email address", "warning")
            await self._add_log("User assignment failed: Invalid email format", "warning")
            return
        try:
            self.assign_btn.disabled = True
            self.page.update()
            await self.api_client.assign_user(self.selected_client_id, email)
            self.assign_user_email.value = ""
            await self._add_log(f"User assigned to client: {email}", "success")
            self.notification.show("User assigned", "success")
        except Exception as exc:
            await self._add_log(f"Assignment failed: {exc}", "error")
            self.notification.show("Failed to assign user", "error")
        finally:
            self.assign_btn.disabled = False
            self.page.update()

    async def _register_file_async(self, _: ft.ControlEvent | None = None) -> None:
        if not self.selected_client_id:
            self.notification.show("Select a client first", "warning")
            return
        display_name = (self.file_display_name.value or "").strip()
        file_path = (self.file_path.value or "").strip()
        sheet_name = (self.file_sheet.value or "").strip() or None
        if not display_name or not file_path:
            self.notification.show("File name and path are required", "warning")
            return
        mappings = []
        if self.map_date.value:
            mappings.append({"excel_column": self.map_date.value, "field_name": "date", "data_type": "date"})
        if self.map_product.value:
            mappings.append(
                {"excel_column": self.map_product.value, "field_name": "product", "data_type": "text"}
            )
        if self.map_quantity.value:
            mappings.append(
                {"excel_column": self.map_quantity.value, "field_name": "quantity", "data_type": "number"}
            )
        if self.map_revenue.value:
            mappings.append(
                {"excel_column": self.map_revenue.value, "field_name": "revenue", "data_type": "number"}
            )
        if self.map_region.value:
            mappings.append(
                {"excel_column": self.map_region.value, "field_name": "region", "data_type": "text"}
            )
        if self.map_salesperson.value:
            mappings.append(
                {
                    "excel_column": self.map_salesperson.value,
                    "field_name": "salesperson",
                    "data_type": "text",
                }
            )
        if not mappings:
            self.notification.show("At least one column mapping is required", "warning")
            return
        payload = {
            "display_name": display_name,
            "file_path": file_path,
            "sheet_name": sheet_name,
            "has_header": bool(self.file_has_header.value),
            "mappings": mappings,
        }
        try:
            self.file_register_btn.disabled = True
            self.page.update()
            await self.api_client.register_file(self.selected_client_id, payload)
            self.file_display_name.value = ""
            self.file_path.value = ""
            self.file_sheet.value = ""
            await self._add_log(f"File registered: {display_name}", "success")
            self.notification.show("File registered", "success")
            await self._load_files_async()
            await self._refresh_dashboard_async(force=True)
        except Exception as exc:
            await self._add_log(f"File registration failed: {exc}", "error")
            self.notification.show("Failed to register file", "error")
        finally:
            self.file_register_btn.disabled = False
            self.page.update()

    async def _create_report_async(self, _: ft.ControlEvent | None = None) -> None:
        if not self.selected_client_id:
            self.notification.show("Select a client first", "warning")
            return
        if not self.report_file_dropdown.value:
            self.notification.show("Select a data source", "warning")
            return
        name = (self.report_name.value or "").strip()
        if not name:
            self.notification.show("Report name is required", "warning")
            return
        try:
            days = int(self.report_days.value or "7")
        except ValueError:
            self.notification.show("Last N days must be a number", "warning")
            return

        metric_value = self.report_metric.value or "revenue_sum"
        field, agg = metric_value.split("_", 1)
        payload = {
            "client_id": self.selected_client_id,
            "file_id": int(self.report_file_dropdown.value),
            "name": name,
            "date_range_days": days,
            "group_by": self.report_group_by.value,
            "metrics": [{"field": field, "agg": agg}],
            "chart_type": "bar",
            "filters": {},
        }
        try:
            self.report_create_btn.disabled = True
            self.page.update()
            await self.api_client.create_report(payload)
            self.report_name.value = ""
            await self._add_log(f"Report created: {name}", "success")
            self.notification.show("Report created", "success")
            await self._load_reports_async()
        except Exception as exc:
            await self._add_log(f"Report creation failed: {exc}", "error")
            self.notification.show("Failed to create report", "error")
        finally:
            self.report_create_btn.disabled = False
            self.page.update()

    async def _run_report_async(self, _: ft.ControlEvent | None = None) -> None:
        if not self.report_select.value:
            return
        report_id = int(self.report_select.value)
        try:
            self.report_run_btn.disabled = True
            self.page.update()
            result = await self.api_client.run_report(report_id)
            self.report_results_list.controls = []
            for idx, row in enumerate(result.get("rows", [])):
                label = row.get("group", "-")
                metrics = [
                    f"{key}: {value}" for key, value in row.items() if key != "group"
                ]
                metrics_text = ", ".join(metrics) if metrics else "-"

                # Alternate background colors
                bg_color = Theme.FIELD_BG if idx % 2 == 0 else Theme.SECONDARY_LIGHT

                self.report_results_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(
                                        str(idx + 1),
                                        color=Theme.TEXT_SECONDARY,
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    width=32,
                                    height=32,
                                    bgcolor=Theme.SECONDARY_LIGHT,
                                    border_radius=8,
                                    alignment=ft.Alignment(0, 0),
                                ),
                                ft.Text(label, color=Theme.TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_500),
                                ft.Container(expand=True),
                                ft.Text(metrics_text, color=Theme.ACCENT_EMERALD, size=12, weight=ft.FontWeight.W_500),
                            ],
                            spacing=12,
                        ),
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        bgcolor=bg_color,
                        border_radius=8,
                    )
                )
            self.page.update()
        except Exception as exc:
            await self._add_log(f"Report run failed: {exc}", "error")
            self.notification.show("Failed to run report", "error")
        finally:
            self.report_run_btn.disabled = False
            self.page.update()

    async def _login_async(self, _: ft.ControlEvent | None = None) -> None:
        email = self.login_email.value.strip() if self.login_email.value else ""
        password = self.login_password.value if self.login_password.value else ""

        # Validation
        if not email or not password:
            self.notification.show("Email and password are required", "warning")
            await self._add_log("Login failed: Missing credentials", "warning")
            return

        # Basic email format validation
        if "@" not in email:
            self.notification.show("Please enter a valid email address", "warning")
            await self._add_log("Login failed: Invalid email format", "warning")
            return

        if len(password) < 6:
            self.notification.show("Password must be at least 6 characters", "warning")
            await self._add_log("Login failed: Password too short", "warning")
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
            self.nav_admin.visible = is_admin
            self.create_btn.disabled = not is_admin
            self.client_create_btn.disabled = not is_admin
            self.assign_btn.disabled = not is_admin
            self.file_register_btn.disabled = not is_admin
            self.logs_card.visible = is_admin
            self.report_create_btn.disabled = True
            self.report_run_btn.disabled = True
            self.refresh_dashboard_btn.disabled = True
            self.current_section = Section.DASHBOARD
            self._update_content_visibility()

            self.logout_btn.disabled = False
            self.login_email.disabled = True
            self.login_password.disabled = True

            self.login_layer.visible = False
            self.app_layer.visible = True

            self.page.update()

            await self._add_log(f"Login successful as {user.get('name')}", "success")
            self.notification.show(f"Welcome back, {user.get('name')}!", "success")

            await self._load_clients_async()

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

        self.nav_admin.visible = False
        self.create_btn.disabled = True
        self.client_create_btn.disabled = True
        self.assign_btn.disabled = True
        self.file_register_btn.disabled = True
        self.logs_card.visible = False
        self.refresh_dashboard_btn.disabled = True
        self.report_create_btn.disabled = True
        self.report_run_btn.disabled = True
        self.current_section = Section.DASHBOARD
        self._update_navigation()
        self._update_content_visibility()

        self.clients = []
        self.files = []
        self.reports = []
        self.selected_client_id = None
        self.selected_client_name.value = "Select a client"
        self.dashboard_title.value = "Dashboard"
        self.client_dropdown.options = []
        self.client_dropdown.value = None
        self.report_file_dropdown.options = []
        self.report_file_dropdown.value = None
        self.report_select.options = []
        self.report_select.value = None
        self.report_results_list.controls = []
        self.data_sources_list.controls = []
        self.revenue_by_product_list.controls = []
        self.revenue_by_date_list.controls = []
        self.total_revenue_value.value = "-"
        self.total_transactions_value.value = "-"
        self.revenue_today_value.value = "-"

        self.login_layer.visible = True
        self.app_layer.visible = False

        await self._add_log("Logged out successfully", "info")
        self.notification.show("You have been logged out", "info")
        self.page.update()

    async def _create_user_async(self, _: ft.ControlEvent | None = None) -> None:
        email = self.create_email.value.strip() if self.create_email.value else ""
        name = self.create_name.value.strip() if self.create_name.value else ""
        password = self.create_password.value if self.create_password.value else ""
        role = self.create_role.value or "user"

        # Validation
        if not email or not name or not password:
            self.notification.show("All fields are required", "warning")
            await self._add_log("User creation failed: Missing fields", "warning")
            return

        if "@" not in email:
            self.notification.show("Please enter a valid email address", "warning")
            await self._add_log("User creation failed: Invalid email format", "warning")
            return

        if len(name) < 2:
            self.notification.show("Name must be at least 2 characters", "warning")
            await self._add_log("User creation failed: Name too short", "warning")
            return

        if len(password) < 8:
            self.notification.show("Password must be at least 8 characters", "warning")
            await self._add_log("User creation failed: Password too short", "warning")
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
