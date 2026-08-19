export type StaffRole = "admin" | "expert";

export type StaffUser = {
  id: string;
  name: string;
  username: string;
  role: StaffRole;
};

export type StaffSession = StaffUser & {
  token: string;
  expiresAt: number;
};
