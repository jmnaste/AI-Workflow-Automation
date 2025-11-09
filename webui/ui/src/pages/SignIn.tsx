import { Box, Typography, Card, CardContent, Button } from '@mui/material';

export default function SignIn() {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: 'background.default',
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%', p: 2 }}>
        <CardContent>
          <Typography variant="h4" sx={{ mb: 3, fontWeight: 700, textAlign: 'center' }}>
            Sign In
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
            Authentication UI will be implemented here.
          </Typography>
          <Button variant="contained" fullWidth size="large">
            Sign In
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}
