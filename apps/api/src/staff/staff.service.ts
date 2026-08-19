import { Injectable } from "@nestjs/common";
import type { StaffUser } from "../auth/auth.types";
import { LeadsService } from "../leads/leads.service";
import { ToursService } from "../tours/tours.service";

const EXPERTS = [
  { id: "expert-1", name: "کارشناس فروش", initials: "ک ف", extension: "101", active: true },
  { id: "expert-2", name: "سارا احمدی", initials: "س ا", extension: "102", active: true },
  { id: "expert-3", name: "امیر رضایی", initials: "ا ر", extension: "103", active: true },
] as const;

@Injectable()
export class StaffService {
  constructor(
    private readonly leadsService: LeadsService,
    private readonly toursService: ToursService,
  ) {}

  experts() {
    const leads = this.leadsService.listAll();
    return EXPERTS.map((expert) => {
      const assigned = leads.filter((lead) => lead.assignedExpertId === expert.id);
      return {
        ...expert,
        assigned: assigned.length,
        open: assigned.filter((lead) => !["won", "lost"].includes(lead.status)).length,
        won: assigned.filter((lead) => lead.status === "won").length,
      };
    });
  }

  adminDashboard() {
    const stats = this.leadsService.statsForUser({
      id: "admin-1",
      name: "مدیر",
      username: "admin",
      role: "admin",
    });
    const tours = this.toursService.findManaged();
    const wonLeads = this.leadsService.listAll().filter((lead) => lead.status === "won");
    const estimatedRevenue = wonLeads.reduce((sum, lead) => {
      const tour = tours.find((item) => item.id === lead.tourId);
      return sum + (tour?.price ?? 0);
    }, 0);

    return {
      leads: stats,
      tours: {
        total: tours.length,
        active: tours.filter((tour) => tour.active).length,
        inquiry: tours.filter((tour) => tour.active && tour.price === null).length,
      },
      experts: this.experts(),
      estimatedRevenue,
      conversion: stats.total ? Math.round((stats.won / stats.total) * 100) : 0,
    };
  }

  expertDashboard(user: StaffUser) {
    const stats = this.leadsService.statsForUser(user);
    const all = this.leadsService.listForUser(user);
    const mine = all.filter((lead) => lead.assignedExpertId === user.id);
    const queue = all.filter((lead) => lead.assignedExpertId === null);

    return {
      stats,
      mine: mine.slice(0, 6),
      queue: queue.slice(0, 5),
    };
  }
}
