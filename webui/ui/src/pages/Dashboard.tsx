import { Box, Typography, Card, CardContent, Grid, Chip } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SpeedIcon from '@mui/icons-material/Speed';
import WorkflowIcon from '@mui/icons-material/AccountTree';

const stats = [
  {
    label: 'Active Workflows',
    value: '12',
    icon: <WorkflowIcon sx={{ fontSize: 20 }} />,
    color: '#5865f2',
  },
  {
    label: 'Total Runs',
    value: '1,247',
    icon: <TrendingUpIcon sx={{ fontSize: 20 }} />,
    color: '#34c759',
  },
  {
    label: 'Success Rate',
    value: '98.5%',
    icon: <CheckCircleIcon sx={{ fontSize: 20 }} />,
    color: '#34c759',
  },
  {
    label: 'Avg. Runtime',
    value: '2.3s',
    icon: <SpeedIcon sx={{ fontSize: 20 }} />,
    color: '#5865f2',
  },
];

export default function Dashboard() {
  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Overview of your workflow automation platform
          </Typography>
        </Box>
        <Chip label="Live" color="success" size="small" />
      </Box>

      <Grid container spacing={2}>
        {stats.map((stat) => (
          <Grid item xs={12} sm={6} lg={3} key={stat.label}>
            <Card sx={{ height: '100%' }}>
              <CardContent sx={{ p: 2.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 36,
                      height: 36,
                      borderRadius: 1,
                      bgcolor: `${stat.color}15`,
                      color: stat.color,
                    }}
                  >
                    {stat.icon}
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8125rem' }}>
                    {stat.label}
                  </Typography>
                </Box>
                <Typography variant="h3" component="div" sx={{ fontWeight: 600, fontSize: '1.875rem' }}>
                  {stat.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={2} sx={{ mt: 1 }}>
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Recent Activity
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Recent workflow runs and activity will be displayed here.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Quick Actions
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Quick action buttons will be available here.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
