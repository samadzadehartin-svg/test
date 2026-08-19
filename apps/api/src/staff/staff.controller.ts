import { Body, Controller, Get, Headers, Param, Patch, UseGuards } from "@nestjs/common";
import { AuthGuard } from "../auth/auth.guard";
import { AuthService } from "../auth/auth.service";
import { Roles } from "../auth/roles.decorator";
import { RolesGuard } from "../auth/roles.guard";
import type { StaffUser } from "../auth/auth.types";
import { ToursService } from "../tours/tours.service";
import { StaffService } from "./staff.service";

@Controller("staff")
@UseGuards(AuthGuard, RolesGuard)
export class StaffController {
  constructor(
    private readonly staffService: StaffService,
    private readonly toursService: ToursService,
    private readonly authService: AuthService,
  ) {}

  @Get("admin/dashboard")
  @Roles("admin")
  adminDashboard() {
    return this.staffService.adminDashboard();
  }

  @Get("expert/dashboard")
  @Roles("expert")
  expertDashboard(@Headers("authorization") authorization?: string) {
    return this.staffService.expertDashboard(this.staffUser(authorization));
  }

  @Get("experts")
  @Roles("admin")
  experts() {
    return this.staffService.experts();
  }

  @Get("tours")
  @Roles("admin")
  tours() {
    return this.toursService.findManaged();
  }

  @Patch("tours/:id")
  @Roles("admin")
  updateTour(
    @Param("id") id: string,
    @Body() body: { price?: number | null; active?: boolean; tag?: string },
  ) {
    return this.toursService.updateManaged(id, body);
  }

  private staffUser(authorization?: string): StaffUser {
    const token = authorization?.startsWith("Bearer ") ? authorization.slice(7) : undefined;
    const session = this.authService.requireSession(token);
    return { id: session.id, name: session.name, username: session.username, role: session.role };
  }
}
