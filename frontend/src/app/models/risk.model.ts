export interface User {
  id?: number;
  email: string;
  username: string;
  full_name?: string;
  role: string;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface MongoStatus {
  connected: boolean;
  url: string;
  database: string;
  message: string;
  collections: { [key: string]: number };
}

export interface RiskFactor {
  feature: string;
  label: string;
  value: string;
  impact: 'INCREASES_RISK' | 'DECREASES_RISK';
  description: string;
  weight?: number;
}

export interface RiskPrediction {
  id?: number;
  project_name: string;
  mr_iid?: number;
  mr_title?: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  defect_probability: number;
  top_risk_factors: RiskFactor[];
  mitigating_factors: RiskFactor[];
  recommendations: string[];
  metrics_summary: {
    lines_added: number;
    lines_deleted: number;
    total_churn: number;
    files_changed: number;
    directories_changed: number;
    entropy: number;
    developer_experience: number;
    subsystem_experience: number;
    tests_modified?: boolean;
    critical_modules_affected?: boolean;
    [key: string]: any;
  };
  created_by_user?: string;
  created_at: string;
}

export interface PredictionSummary {
  id: number;
  project_name: string;
  mr_iid?: number;
  mr_title?: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  defect_probability: number;
  created_at: string;
}

export interface Analytics {
  total_predictions: number;
  avg_risk_score: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  high_risk_pct: number;
  common_recommendations: { recommendation: string; count: number }[];
}

export interface DirectPredictRequest {
  la: number;
  ld: number;
  nf: number;
  nd: number;
  ns: number;
  ent: number;
  ndev?: number;
  age?: number;
  nuc?: number;
  aexp?: number;
  arexp?: number;
  asexp?: number;
  project_name?: string;
  mr_iid?: number;
  mr_title?: string;
  tests_modified?: boolean;
  critical_modules?: boolean;
}

export interface GitDiffPredictRequest {
  diff_text: string;
  project_name?: string;
  mr_iid?: number;
  mr_title?: string;
  aexp?: number;
  arexp?: number;
  asexp?: number;
}

export interface GitLabMRRequest {
  gitlab_url?: string;
  project_id: string;
  mr_iid: number;
  private_token?: string;
}
