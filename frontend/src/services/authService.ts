import apiClient from './api';
import {
  AuthTokens,
  CreateAgentRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from '../types/auth';

export const authService = {
  async register(data: RegisterRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/register/', data);
    return response.data;
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login/', {
      email,
      password,
    });
    return response.data;
  },

  async refreshToken(refresh: string): Promise<AuthTokens> {
    const response = await apiClient.post<AuthTokens>('/auth/refresh/', { refresh });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me/');
    return response.data;
  },

  async listAgents(): Promise<User[]> {
    const response = await apiClient.get<User[] | { results: User[] }>('/auth/users/');
    const data = response.data;
    if (Array.isArray(data)) {
      return data;
    }
    if (data && typeof data === 'object' && Array.isArray((data as { results: User[] }).results)) {
      return (data as { results: User[] }).results;
    }
    return [];
  },

  async createAgent(data: CreateAgentRequest): Promise<User> {
    const response = await apiClient.post<User>('/auth/users/', data);
    return response.data;
  },
};
