import { Box, Typography } from '@mui/material';

export default function Settings() {
  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3, fontWeight: 700 }}>
        Settings
      </Typography>
      <Typography color="text.secondary">
        Application settings will be implemented here.
      </Typography>
    </Box>
  );
}
