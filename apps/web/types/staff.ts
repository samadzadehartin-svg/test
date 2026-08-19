export type StaffRole = "admin" | "expert";
export type LeadStatus = "new" | "contacted" | "qualified" | "reserved" | "won" | "lost";

export type StaffUser = {
  id: string;
  name: string;
  username: string;
  role: StaffRole;
};

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

export type ExpertSummary = {
  id: string;
  name: string;
  initials: string;
  extension: string;
  active: boolean;
  assigned: number;
  open: number;
  won: number;
};

export type AdminDashboard = {
  leads: Record<string, number> & { total: number; new: number; qualified: number; reserved: number; won: number; unassigned: number };
  tours: { total: number; active: number; inquiry: number };
  experts: ExpertSummary[];
  estimatedRevenue: number;
  conversion: number;
};

export type ExpertDashboard = {
  stats: Record<string, number> & { total: number; new: number; qualified: number; reserved: number; won: number; today: number };
  mine: Lead[];
  queue: Lead[];
};
