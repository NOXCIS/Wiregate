# Security Policy

## Supported Versions
Versions currently being supported with security updates.

| Version | Supported          | Security Features |
| ------- | ------------------ | ----------------- |
| sol-beta-v2.3.3+ | :white_check_mark: | Full Security Suite |
| vidar (stable) | :white_check_mark: | Core Security Features |
| jasper-beta | :white_check_mark: | Core Security Features |
| acid-rain-beta-v0.4.2 | :white_check_mark: | Basic Security Features |
| < vidar | :x: | No longer supported |

## Security Features by Version

### sol-beta-v2.3.3+ (Latest)
- ✅ Distributed Rate Limiting with Redis
- ✅ Brute Force Protection with PostgreSQL
- ✅ Secure Command Execution
- ✅ Restricted Shell Environment
- ✅ Input Validation & Sanitization
- ✅ File Upload Security
- ✅ Session Management
- ✅ Security Headers
- ✅ Path Traversal Protection
- ✅ Command Injection Prevention

### vidar (Stable)
- ✅ Basic Rate Limiting
- ✅ Secure Command Execution
- ✅ Restricted Shell Environment
- ✅ Input Validation
- ✅ File Upload Security
- ✅ Session Management
- ✅ Security Headers

## Reporting Security Vulnerabilities

If you discover a security vulnerability in WireGate, please report it responsibly:

1. **DO NOT** create a public GitHub issue
2. Email security details to: security@wiregate.dev
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Response Process

1. **Acknowledgment**: We will acknowledge receipt within 48 hours
2. **Assessment**: We will assess the vulnerability within 7 days
3. **Fix Development**: Critical issues fixed within 30 days
4. **Disclosure**: Coordinated disclosure after fix is available
5. **Update**: Security advisory published with fix details

## Security Best Practices

### For Administrators
- Always use the latest stable version
- Regularly update dependencies
- Monitor security advisories
- Use strong authentication
- Enable logging and monitoring
- Restrict network access to dashboard

### For Developers
- Follow secure coding practices
- Validate all inputs
- Use parameterized queries
- Implement proper error handling
- Regular security audits
- Keep dependencies updated

