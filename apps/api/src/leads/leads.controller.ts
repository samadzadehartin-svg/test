import { Body, Controller, Get, Headers, Param, Patch, Post, UseGuards } from "@nestjs/common";
import { AuthGuard } from "../auth/auth.guard";
import { AuthService } from "../auth/auth.service";
import type { StaffUser } from "../auth/auth.types";
import { LeadsService } from "./leads.service";

@Controller("leads")
export class LeadsController {
  constructor(
    private readonly leadsService: LeadsService,
    private readonly authService: AuthService,
  ) {}

  @Post()
  create(@Body() body: { tourId?: string; phone?: string }) {
    return this.leadsService.create(body);
  }

  @Get()
  @UseGuards(AuthGuard)
  list(@Headers("authorization") authorization?: string) {
    return this.leadsService.listForUser(this.staffUser(authorization));
  }

  @Get("stats")
  @UseGuards(AuthGuard)
  stats(@Headers("authorization") authorization?: string) {
    return this.leadsService.statsForUser(this.staffUser(authorization));
  }

  @Post(":id/claim")
  @UseGuards(AuthGuard)
  claim(@Param("id") id: string, @Headers("authorization") authorization?: string) {
    return this.leadsService.claim(id, this.staffUser(authorization));
  }

  @Patch(":id")
  @UseGuards(AuthGuard)
  update(
    @Param("id") id: string,
    @Body() body: { status?: string; note?: string; assignedExpertId?: string | null },
    @Headers("authorization") authorization?: string,
  ) {
    return this.leadsService.update(id, body, this.staffUser(authorization));
  }

  private staffUser(authorization?: string): StaffUser {
    const token = authorization?.startsWith("Bearer ") ? authorization.slice(7) : undefined;
    const session = this.authService.requireSession(token);
    return { id: session.id, name: session.name, username: session.username, role: session.role };
  }
}
