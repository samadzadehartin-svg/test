import { BadRequestException, ForbiddenException, Injectable, NotFoundException } from "@nestjs/common";
import { randomUUID } from "node:crypto";
import type { StaffUser } from "../auth/auth.types";

export type LeadStatus = "new" | "contacted" | "qualified" | "reserved" | "won" | "lost";

export type Lead = {
  id: string;
  tourId: string;
  phone: string;
  status: LeadStatus;
  assignedExpertId: string | null;
  note: string;
  createdAt: string;
  updatedAt: string;
};

const validStatuses = new Set<LeadStatus>(["new", "contacted", "qualified", "reserved", "won", "lost"]);

@Injectable()
export class LeadsService {
  private readonly leads: Lead[] = [];

  constructor() {
    if ((process.env.DEMO_SEED ?? "true") !== "false") this.seedDemoLeads();
  }

  create(input: { tourId?: string; phone?: string }) {
    const tourId = input.tourId?.trim();
    const phone = input.phone?.trim();

    if (!tourId) throw new BadRequestException("tourId is required");
    if (!phone || !/^09\d{9}$/.test(phone)) {
      throw new BadRequestException("Invalid phone");
    }

    const now = new Date().toISOString();
    const lead: Lead = {
      id: randomUUID(),
      tourId,
      phone,
      status: "new",
      assignedExpertId: null,
      note: "",
      createdAt: now,
      updatedAt: now,
    };

    this.leads.unshift(lead);

    return {
      id: lead.id,
      status: "received",
      createdAt: lead.createdAt,
    };
  }

  listForUser(user: StaffUser) {
    if (user.role === "admin") return [...this.leads];
    return this.leads.filter((lead) => lead.assignedExpertId === user.id || lead.assignedExpertId === null);
  }

  listAll() {
    return [...this.leads];
  }

  findOne(id: string) {
    const lead = this.leads.find((item) => item.id === id);
    if (!lead) throw new NotFoundException("Lead not found");
    return lead;
  }

  claim(id: string, user: StaffUser) {
    if (user.role !== "expert") throw new ForbiddenException("Only experts can claim leads");
    const lead = this.findOne(id);
    if (lead.assignedExpertId && lead.assignedExpertId !== user.id) {
      throw new ForbiddenException("Lead already assigned");
    }
    lead.assignedExpertId = user.id;
    lead.updatedAt = new Date().toISOString();
    return lead;
  }

  update(
    id: string,
    input: { status?: string; note?: string; assignedExpertId?: string | null },
    user: StaffUser,
  ) {
    const lead = this.findOne(id);

    if (user.role === "expert" && lead.assignedExpertId !== user.id) {
      throw new ForbiddenException("این درخواست به شما واگذار نشده است");
    }

    if (input.status) {
      if (!validStatuses.has(input.status as LeadStatus)) {
        throw new BadRequestException("Invalid status");
      }
      lead.status = input.status as LeadStatus;
    }

    if (typeof input.note === "string") {
      lead.note = input.note.trim().slice(0, 1000);
    }

    if (user.role === "admin" && input.assignedExpertId !== undefined) {
      lead.assignedExpertId = input.assignedExpertId || null;
    }

    lead.updatedAt = new Date().toISOString();
    return lead;
  }

  statsForUser(user: StaffUser) {
    const relevant = user.role === "admin"
      ? this.leads
      : this.leads.filter((lead) => lead.assignedExpertId === user.id);

    const today = new Date().toISOString().slice(0, 10);
    return {
      total: relevant.length,
      new: relevant.filter((lead) => lead.status === "new").length,
      contacted: relevant.filter((lead) => lead.status === "contacted").length,
      qualified: relevant.filter((lead) => lead.status === "qualified").length,
      reserved: relevant.filter((lead) => lead.status === "reserved").length,
      won: relevant.filter((lead) => lead.status === "won").length,
      lost: relevant.filter((lead) => lead.status === "lost").length,
      today: relevant.filter((lead) => lead.createdAt.startsWith(today)).length,
      unassigned: user.role === "admin" ? this.leads.filter((lead) => !lead.assignedExpertId).length : 0,
    };
  }

  private seedDemoLeads() {
    const now = Date.now();
    const seed: Array<Pick<Lead, "tourId" | "phone" | "status" | "assignedExpertId" | "note"> & { ageMinutes: number }> = [
      { tourId: "istanbul-cartoon", phone: "09120000001", status: "new", assignedExpertId: null, note: "", ageMinutes: 7 },
      { tourId: "antalya-nirvana", phone: "09120000002", status: "contacted", assignedExpertId: "expert-1", note: "بودجه را بررسی می‌کند.", ageMinutes: 38 },
      { tourId: "van-tamara", phone: "09120000003", status: "qualified", assignedExpertId: "expert-1", note: "برای دو نفر؛ تاریخ منعطف.", ageMinutes: 82 },
      { tourId: "oman-carnelian", phone: "09120000004", status: "reserved", assignedExpertId: "expert-1", note: "در انتظار تأیید پاسپورت.", ageMinutes: 190 },
      { tourId: "armenia-primer", phone: "09120000005", status: "won", assignedExpertId: "expert-2", note: "فروش نهایی شد.", ageMinutes: 560 },
      { tourId: "kish-sadaf", phone: "09120000006", status: "new", assignedExpertId: null, note: "", ageMinutes: 24 },
      { tourId: "thailand-phuket", phone: "09120000007", status: "lost", assignedExpertId: "expert-3", note: "بودجه کافی نبود.", ageMinutes: 1400 },
      { tourId: "russia-4", phone: "09120000008", status: "qualified", assignedExpertId: "expert-2", note: "نیاز به راهنمایی ویزا.", ageMinutes: 330 },
    ];

    for (const item of seed) {
      const createdAt = new Date(now - item.ageMinutes * 60_000).toISOString();
      this.leads.push({
        id: randomUUID(),
        tourId: item.tourId,
        phone: item.phone,
        status: item.status,
        assignedExpertId: item.assignedExpertId,
        note: item.note,
        createdAt,
        updatedAt: createdAt,
      });
    }
  }
}
