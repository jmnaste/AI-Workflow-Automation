import { Box, Typography, Card, CardContent, Grid } from '@mui/material';

export default function Dashboard() {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 700 }}>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Active Workflows
              </Typography>
              <Typography variant="h3" component="div">
                12
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Runs
              </Typography>
              <Typography variant="h3" component="div">
                1,247
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Success Rate
              </Typography>
              <Typography variant="h3" component="div">
                98.5%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Avg. Runtime
              </Typography>
              <Typography variant="h3" component="div">
                2.3s
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
