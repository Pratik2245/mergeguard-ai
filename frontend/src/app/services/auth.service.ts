import { Injectable, signal, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { User, TokenResponse } from '../models/risk.model';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:8000/api/v1/auth';
  private tokenKey = 'mergeguard_jwt_token';

  currentUser = signal<User | null>(null);

  constructor() {
    this.restoreSession();
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  getAuthHeaders(): HttpHeaders {
    const token = this.getToken();
    if (token) {
      return new HttpHeaders({ Authorization: `Bearer ${token}` });
    }
    return new HttpHeaders();
  }

  register(payload: { email: string; username: string; password: string; full_name?: string }): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/register`, payload).pipe(
      tap((res) => {
        this.saveSession(res.access_token, res.user);
      })
    );
  }

  login(payload: { username_or_email: string; password: string }): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, payload).pipe(
      tap((res) => {
        this.saveSession(res.access_token, res.user);
      })
    );
  }

  getProfile(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/me`, { headers: this.getAuthHeaders() }).pipe(
      tap((user) => this.currentUser.set(user))
    );
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    this.currentUser.set(null);
  }

  private saveSession(token: string, user: User) {
    localStorage.setItem(this.tokenKey, token);
    this.currentUser.set(user);
  }

  private restoreSession() {
    const token = this.getToken();
    if (token) {
      this.getProfile().subscribe({
        error: () => this.logout(),
      });
    }
  }
}
