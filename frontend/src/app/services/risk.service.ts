import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  RiskPrediction,
  PredictionSummary,
  Analytics,
  DirectPredictRequest,
  GitDiffPredictRequest,
  GitLabMRRequest,
  MongoStatus,
} from '../models/risk.model';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root',
})
export class RiskService {
  private http = inject(HttpClient);
  private authService = inject(AuthService);
  private apiUrl = 'http://localhost:8000/api/v1';

  getHealth(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }

  getModelInfo(): Observable<any> {
    return this.http.get(`${this.apiUrl}/model-info`);
  }

  getMongoStatus(): Observable<MongoStatus> {
    return this.http.get<MongoStatus>(`${this.apiUrl}/mongodb/status`);
  }

  predictDirect(payload: DirectPredictRequest): Observable<RiskPrediction> {
    return this.http.post<RiskPrediction>(`${this.apiUrl}/predict/direct`, payload, {
      headers: this.authService.getAuthHeaders(),
    });
  }

  predictDiff(payload: GitDiffPredictRequest): Observable<RiskPrediction> {
    return this.http.post<RiskPrediction>(`${this.apiUrl}/predict/diff`, payload, {
      headers: this.authService.getAuthHeaders(),
    });
  }

  predictGitLab(payload: GitLabMRRequest): Observable<RiskPrediction> {
    return this.http.post<RiskPrediction>(`${this.apiUrl}/predict/gitlab`, payload, {
      headers: this.authService.getAuthHeaders(),
    });
  }

  getPredictions(riskLevel?: string): Observable<PredictionSummary[]> {
    let params = new HttpParams();
    if (riskLevel && riskLevel !== 'ALL') {
      params = params.set('risk_level', riskLevel);
    }
    return this.http.get<PredictionSummary[]>(`${this.apiUrl}/predictions`, { params });
  }

  getPredictionDetail(id: number): Observable<RiskPrediction> {
    return this.http.get<RiskPrediction>(`${this.apiUrl}/predictions/${id}`);
  }

  getAnalytics(): Observable<Analytics> {
    return this.http.get<Analytics>(`${this.apiUrl}/analytics`);
  }
}
