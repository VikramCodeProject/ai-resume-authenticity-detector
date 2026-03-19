/**
 * Resume Truth Verification System - Frontend
 * React.js 18+ with TypeScript & Material UI v5
 */

import React, { useState, useEffect, useRef } from "react";
import {
  Container,
  Box,
  Paper,
  Button,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from "@mui/material";

import {
  CloudUpload as CloudUploadIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Warning as WarningIcon,
  Download as DownloadIcon,
} from "@mui/icons-material";

import axios from "axios";
import Chart from 'chart.js/auto';

// ===================== API BASE =====================
// Use direct backend URL since Vite dev server proxy is having issues
// Points to mock server running at http://127.0.0.1:8000
const API = "http://127.0.0.1:8000";

// ===================== TYPES =====================

interface Claim {
  id: string;
  claim_type: "skill" | "education" | "experience" | "certification" | "project";
  claim_text: string;
  confidence: number;
}

interface MLPrediction {
  claim_id: string;
  prediction: "verified" | "doubtful" | "fake";
  confidence: number;
  shap_explanation?: string;
}

interface ResumeData {
  resume_id: string;
  filename: string;
  status: "uploaded" | "processing" | "completed" | "failed";
  uploaded_at: string;
  trust_score?: {
    overall_score: number;
    verified_count: number;
    doubtful_count: number;
    fake_count: number;
    generated_at: string;
  };
  claims?: Claim[];
  predictions?: MLPrediction[];
  blockchain_hash?: string;
  processing_stage?: string;
  processing_progress?: number;
}

interface UploadResponse {
  resume_id: string;
  status: string;
  message: string;
  processing_job_id: string;
}

const getApiErrorMessage = (err: any, fallback: string): string => {
  const payload = err?.response?.data;
  if (!payload) return fallback;
  if (typeof payload?.message === "string") return payload.message;
  if (typeof payload?.detail === "string") return payload.detail;
  return fallback;
};

// ===================== TRUST SCORE GAUGE =====================

const TrustScoreGauge: React.FC<{ score: number }> = ({ score }) => {
  const getColor = (score: number) => {
    if (score >= 80) return "#4caf50";
    if (score >= 60) return "#ff9800";
    return "#f44336";
  };

  const getLabel = (score: number) => {
    if (score >= 80) return "Verified";
    if (score >= 60) return "Doubtful";
    return "Fake";
  };

  return (
    <Box sx={{ textAlign: "center", py: 3 }}>
      <Box sx={{ position: "relative", display: "inline-flex" }}>
        <CircularProgress
          variant="determinate"
          value={score}
          size={200}
          thickness={4}
          sx={{ color: getColor(score) }}
        />

        <Box
          sx={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
          }}
        >
          <Typography variant="h3" fontWeight="bold">
            {score.toFixed(1)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {getLabel(score)}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

// ===================== LOGIN COMPONENT =====================

const LoginComponent: React.FC<{ onLoginSuccess: (token: string) => void }> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
      const res = await axios.post(`${API}${endpoint}`, { email, password });
      
      if (res.data.access_token) {
        localStorage.setItem("authToken", res.data.access_token);
        onLoginSuccess(res.data.access_token);
      } else {
        setError("Invalid response");
      }
    } catch (err: any) {
      setError(getApiErrorMessage(err, "Failed to authenticate"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" textAlign="center" mb={3}>
          Resume Verification System
        </Typography>
        
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            fullWidth
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            margin="normal"
            required
          />
          
          <Button
            fullWidth
            variant="contained"
            sx={{ mt: 3 }}
            disabled={loading}
            type="submit"
          >
            {loading ? <CircularProgress size={24} /> : isLogin ? "Login" : "Register"}
          </Button>

          <Button
            fullWidth
            variant="text"
            sx={{ mt: 2 }}
            onClick={() => {
              setIsLogin(!isLogin);
              setError("");
            }}
          >
            {isLogin ? "Need an account? Register" : "Have an account? Login"}
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

// ===================== UPLOAD COMPONENT =====================

const ResumeUploadComponent: React.FC<{ onUploadSuccess: (id: string) => void; token: string }> = ({
  onUploadSuccess,
  token,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<number>(0);

  const MAX_SIZE = 5 * 1024 * 1024; // 5MB

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (
      ![
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ].includes(selected.type)
    ) {
      setError("Only PDF and DOCX files allowed");
      return;
    }

    if (selected.size > MAX_SIZE) {
      setError("File size must be less than 5MB");
      return;
    }

    setFile(selected);
    setError("");
    setProgress(0);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file, file.name);

      const res = await axios.post<UploadResponse>(
        `${API}/api/resumes/upload`,
        formData,
        {
          headers: { 
            "Content-Type": "multipart/form-data",
            "Authorization": `Bearer ${token}`
          },
          onUploadProgress: (evt) => {
            if (evt.total) {
              const p = Math.round((evt.loaded / evt.total) * 100);
              setProgress(p);
            }
          },
        }
      );

      onUploadSuccess(res.data.resume_id);
      setFile(null);
      setProgress(0);
    } catch (err: any) {
      setError(getApiErrorMessage(err, "Upload failed"));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5">Upload Resume</Typography>

      {error && <Alert severity="error">{error}</Alert>}

      <Box
        sx={{
          border: "2px dashed #ccc",
          p: 3,
          textAlign: "center",
          mt: 2,
          cursor: "pointer",
        }}
      >
        <input
          hidden
          type="file"
          id="file"
          accept=".pdf, .docx, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleFileChange}
        />
        <label htmlFor="file">
          <CloudUploadIcon sx={{ fontSize: 50, color: "#1976d2" }} />
          <Typography>{file ? file.name : "Click to upload PDF/DOCX"}</Typography>
        </label>
      </Box>

      {uploading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant="determinate" value={progress} />
          <Typography variant="body2" sx={{ mt: 1, textAlign: "center" }}>
            Uploading... {progress}%
          </Typography>
        </Box>
      )}

      <Button
        variant="contained"
        fullWidth
        sx={{ mt: 2 }}
        disabled={!file || uploading}
        onClick={handleUpload}
      >
        {uploading ? <CircularProgress size={20} /> : "Upload & Verify"}
      </Button>
    </Paper>
  );
};

// ===================== RESULTS COMPONENT =====================

const VerificationResultsComponent: React.FC<{ data: ResumeData }> = ({ data }) => {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<MLPrediction | null>(null);

  const chipColor = (
    p: string
  ): "success" | "warning" | "error" | "default" => {
    if (p === "verified") return "success";
    if (p === "doubtful") return "warning";
    if (p === "fake") return "error";
    return "default";
  };

  return (
    <>
      {/* Trust Score */}
      {data.trust_score && (
        <Paper sx={{ p: 3, mb: 2 }}>
          <Typography variant="h5">Trust Score</Typography>
          <TrustScoreGauge score={data.trust_score.overall_score} />
        </Paper>
      )}

      {/* Claims Table */}
      {data.predictions && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h5">Claims Analysis</Typography>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Claim</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Prediction</TableCell>
                  <TableCell>Confidence</TableCell>
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {data.predictions.map((p) => (
                  <TableRow key={p.claim_id}>
                    <TableCell>
                      {data.claims?.find((c) => c.id === p.claim_id)?.claim_text}
                    </TableCell>
                    <TableCell>
                      {data.claims?.find((c) => c.id === p.claim_id)?.claim_type}
                    </TableCell>
                    <TableCell>
                      <Chip label={p.prediction} color={chipColor(p.prediction)} />
                    </TableCell>
                    <TableCell>{(p.confidence * 100).toFixed(1)}%</TableCell>
                    <TableCell>
                      <Button
                        onClick={() => {
                          setSelected(p);
                          setOpen(true);
                        }}
                      >
                        Explain
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Explanation Dialog */}
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>AI Explanation</DialogTitle>
        <DialogContent>
          <Typography>{selected?.shap_explanation}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

// ===================== MAIN APP =====================

const App: React.FC = () => {
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [data, setData] = useState<ResumeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Load token from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem("authToken");
    if (token) {
      setAuthToken(token);
    }
  }, []);

  // Logout
  const handleLogout = () => {
    localStorage.removeItem("authToken");
    setAuthToken(null);
    setResumeId(null);
    setData(null);
  };
  // Charts refs
  const pieRef = useRef<HTMLCanvasElement | null>(null);
  const barRef = useRef<HTMLCanvasElement | null>(null);
  const pieChartRef = useRef<any>(null);
  const barChartRef = useRef<any>(null);

  // Blockchain / wallet
  const [walletAddr, setWalletAddr] = useState<string | null>(null);
  const [contractAddr, setContractAddr] = useState<string | null>(null);
  const [txHash, setTxHash] = useState<string | null>(null);

  // Polling Effect
  useEffect(() => {
    if (!resumeId || !authToken) return;
    let timer: NodeJS.Timeout;

    const poll = async () => {
      setLoading(true);
      try {
        const res = await axios.get<ResumeData>(`${API}/api/resumes/${resumeId}`, {
          headers: { "Authorization": `Bearer ${authToken}` }
        });
        setData(res.data);

        if (res.data.status === "processing") {
          timer = setTimeout(poll, 3000);
        }
      } catch (err: any) {
        setError(getApiErrorMessage(err, "Fetch failed"));
      } finally {
        setLoading(false);
      }
    };

    poll();
    return () => clearTimeout(timer);
  }, [resumeId, authToken]);

  // Initialize charts once
  useEffect(() => {
    if (!pieRef.current || !barRef.current) return;
    if (!pieChartRef.current) {
      pieChartRef.current = new Chart(pieRef.current.getContext('2d') as any, {
        type: 'doughnut',
        data: { labels: ['Trust','Remainder'], datasets: [{ data: [85,15], backgroundColor: ['#22D3EE','#0b1220'], borderWidth: 0 }] },
        options: { cutout: '70%', plugins: { legend: { display: false } }, responsive: true, maintainAspectRatio: false }
      });
    }
    if (!barChartRef.current) {
      barChartRef.current = new Chart(barRef.current.getContext('2d') as any, {
        type: 'bar',
        data: { labels: ['GitHub','LinkedIn','Cert','Anomaly'], datasets: [{ label: 'Score', data: [78,82,92,15], backgroundColor: ['#3B82F6','#8B5CF6','#22D3EE','#F97316'] }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
      });
    }
  }, []);

  // Update charts when data changes
  useEffect(() => {
    if (!data) return;
    const trust = data.trust_score?.overall_score ?? 0;
    if (pieChartRef.current) {
      pieChartRef.current.data.datasets[0].data = [trust, Math.max(0,100-trust)];
      pieChartRef.current.update();
    }
    const gh = data.predictions ? Math.round((data.predictions.reduce((s,p)=>s + (p.prediction==='verified'?1:0),0) / data.predictions.length) * 100) : 0;
    if (barChartRef.current) {
      // keep existing length, update first three bars with GitHub/LinkedIn/Cert approximations if available
      barChartRef.current.data.datasets[0].data = [data.trust_score?.overall_score ?? 0, data.trust_score?.overall_score ?? 0, data.trust_score?.overall_score ?? 0, Math.max(0,100-(data.trust_score?.overall_score ?? 0))];
      barChartRef.current.update();
    }
  }, [data]);

  // Wallet connect
  const connectWallet = async () => {
    try {
      const anyWin: any = window as any;
      if (anyWin.ethereum) {
        const accounts = await anyWin.ethereum.request({ method: 'eth_requestAccounts' });
        setWalletAddr(accounts[0]);
        // demo placeholders
        setContractAddr('0x1234...ABCD');
        setTxHash('0xdeadbeef...');
      } else {
        alert('MetaMask not installed');
      }
    } catch (e) {
      console.warn('Wallet connect failed', e);
    }
  };

  return (
    <>
      {!authToken ? (
        <LoginComponent onLoginSuccess={setAuthToken} />
      ) : (
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Typography variant="h3" fontWeight="bold">
              Resume Truth Verification System
            </Typography>
            <Button variant="outlined" color="error" onClick={handleLogout}>
              Logout
            </Button>
          </Box>

          <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2, mt: 2 }}>
            <Button variant="contained" onClick={connectWallet}>
              Connect Wallet
            </Button>
            {walletAddr && (
              <Typography variant="body2" sx={{ alignSelf: "center" }}>
                {walletAddr}
              </Typography>
            )}
          </Box>

          {error && <Alert severity="error">{error}</Alert>}
          {loading && <LinearProgress sx={{ mb: 2 }} />}
          {data?.status === "processing" && (
            <Alert severity="info" sx={{ mb: 2 }}>
              {data.processing_stage || "Verification in progress..."}
              {typeof data.processing_progress === "number" ? ` (${data.processing_progress}%)` : ""}
            </Alert>
          )}

          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <ResumeUploadComponent onUploadSuccess={setResumeId} token={authToken} />
            </Grid>

            <Grid item xs={12} md={8}>
              {!data && <Paper sx={{ p: 3 }}>Upload resume to start</Paper>}
              {data && <VerificationResultsComponent data={data} />}

              <Paper sx={{ p: 2, mt: 2 }}>
                <Typography variant="h6">Analytics</Typography>
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid item xs={12} md={6} sx={{ height: 220 }}>
                    <canvas ref={pieRef as any} style={{ width: "100%", height: "100%" }} />
                  </Grid>
                  <Grid item xs={12} md={6} sx={{ height: 220 }}>
                    <canvas ref={barRef as any} style={{ width: "100%", height: "100%" }} />
                  </Grid>
                </Grid>
              </Paper>

              {data?.blockchain_hash && (
                <Alert severity="success">Blockchain Hash: {data.blockchain_hash}</Alert>
              )}

              <Paper sx={{ p: 2, mt: 2 }}>
                <Typography variant="h6">Blockchain Status</Typography>
                <Typography className="small">Contract: {contractAddr ?? "—"}</Typography>
                <Typography className="small">Tx Hash: {txHash ?? "—"}</Typography>
                <Typography className="small">Wallet: {walletAddr ?? "Not connected"}</Typography>
              </Paper>

              {data && (
                <Button fullWidth variant="outlined" startIcon={<DownloadIcon />}>
                  Download Report
                </Button>
              )}
            </Grid>
          </Grid>
        </Container>
      )}
    </>
  );
};

export default App;
