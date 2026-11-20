export type UserRole = 'ADMIN' | 'SUPPORT_AGENT';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  organization: Organization;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResponse {
  tokens: AuthTokens;
  user: User;
}

export interface RegisterRequest {
  organization_name: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface CreateAgentRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}
