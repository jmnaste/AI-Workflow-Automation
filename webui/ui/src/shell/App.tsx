import * as React from 'react'
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Typography from '@mui/material/Typography'
import Stack from '@mui/material/Stack'
import Avatar from '@mui/material/Avatar'

export default function App() {
  return (
    <Container maxWidth="md">
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, py: 6 }}>
        <Avatar alt="Flovify" src="/images/Flovify-logo.png" sx={{ width: 64, height: 64 }} />
        <Typography variant="h4" component="h1">Flovify</Typography>
        <Typography variant="body1" color="text.secondary">
          UI scaffold ready. When the API is available locally under /api, we’ll wire health checks and run lists.
        </Typography>
      </Box>
    </Container>
  )
}
