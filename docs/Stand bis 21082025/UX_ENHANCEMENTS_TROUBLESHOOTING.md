# GITTE UX Enhancements Troubleshooting Guide

## Overview

This guide provides solutions to common issues you may encounter with the GITTE UX enhancement features. Issues are organized by feature area with step-by-step resolution instructions.

## Table of Contents

1. [Image Correction System Issues](#image-correction-system-issues)
2. [Tooltip System Problems](#tooltip-system-problems)
3. [Prerequisite Validation Issues](#prerequisite-validation-issues)
4. [Accessibility Feature Problems](#accessibility-feature-problems)
5. [Performance Issues](#performance-issues)
6. [Deployment and Configuration Issues](#deployment-and-configuration-issues)
7. [Browser Compatibility Issues](#browser-compatibility-issues)
8. [System Integration Problems](#system-integration-problems)

## Image Correction System Issues

### Issue: Image Correction Dialog Not Appearing

**Symptoms:**
- Generated images don't show correction options
- No quality analysis feedback
- Manual correction tools unavailable

**Possible Causes:**
1. Image correction feature disabled
2. Image quality above threshold
3. JavaScript errors in browser
4. Service connectivity issues

**Resolution Steps:**

1. **Check Feature Configuration**
   ```bash
   # Verify environment variables
   echo $IMAGE_CORRECTION_ENABLED
   echo $IMAGE_QUALITY_THRESHOLD
   ```

2. **Verify Service Status**
   - Check if image quality detection service is running
   - Verify rembg model availability
   - Test image processing pipeline

3. **Browser Debugging**
   - Open browser developer tools (F12)
   - Check console for JavaScript errors
   - Verify network requests are completing
   - Clear browser cache and cookies

4. **Configuration Fix**
   ```yaml
   # In docker-compose.yml
   environment:
     - IMAGE_CORRECTION_ENABLED=true
     - IMAGE_QUALITY_THRESHOLD=0.6
   ```

### Issue: Manual Cropping Not Working

**Symptoms:**
- Crop selection area not responding
- Preview not updating
- Apply button not functional

**Possible Causes:**
1. Browser compatibility issues
2. JavaScript disabled
3. Canvas API not supported
4. Touch/mouse event conflicts

**Resolution Steps:**

1. **Browser Compatibility Check**
   - Test in Chrome, Firefox, Safari, Edge
   - Ensure browser supports HTML5 Canvas
   - Check for browser extensions blocking JavaScript

2. **Enable Required Features**
   ```javascript
   // Check browser capabilities
   console.log('Canvas support:', !!document.createElement('canvas').getContext);
   console.log('Touch events:', 'ontouchstart' in window);
   ```

3. **Clear Browser Data**
   - Clear cache, cookies, and local storage
   - Disable browser extensions temporarily
   - Try incognito/private browsing mode

### Issue: Background Removal Failing

**Symptoms:**
- Background removal produces poor results
- Processing takes too long
- Service errors during isolation

**Possible Causes:**
1. rembg model not loaded
2. Insufficient system resources
3. Unsupported image format
4. Network connectivity issues

**Resolution Steps:**

1. **Check Model Availability**
   ```bash
   # Verify rembg installation
   python -c "import rembg; print('rembg available')"
   
   # Check model files
   ls ~/.u2net/
   ```

2. **System Resources**
   - Ensure adequate RAM (minimum 4GB)
   - Check CPU usage during processing
   - Monitor disk space for temporary files

3. **Image Format Validation**
   ```python
   # Supported formats
   SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'gif', 'webp']
   ```

## Tooltip System Problems

### Issue: Tooltips Not Displaying

**Symptoms:**
- No tooltips appear on hover
- Help text missing from UI elements
- Context-sensitive help not working

**Possible Causes:**
1. Tooltip system disabled
2. JavaScript errors
3. CSS conflicts
4. Content not loaded

**Resolution Steps:**

1. **Verify Configuration**
   ```bash
   # Check tooltip system status
   echo $TOOLTIP_SYSTEM_ENABLED
   echo $TOOLTIP_CACHE_TTL_SECONDS
   ```

2. **Debug JavaScript**
   ```javascript
   // Check tooltip system initialization
   console.log(window.tooltipSystem);
   
   // Test tooltip retrieval
   tooltipSystem.getTooltip('test_element');
   ```

3. **CSS Debugging**
   - Check for CSS conflicts with tooltip styles
   - Verify z-index values for tooltip display
   - Test with browser developer tools

### Issue: Incorrect Tooltip Content

**Symptoms:**
- Tooltips show wrong information
- Content doesn't match current context
- Outdated help text displayed

**Possible Causes:**
1. Cache not updated
2. Context detection failure
3. Content management issues
4. Database synchronization problems

**Resolution Steps:**

1. **Clear Tooltip Cache**
   ```bash
   # Clear Redis cache
   redis-cli FLUSHDB
   
   # Or restart Redis service
   docker-compose restart redis
   ```

2. **Verify Context Detection**
   ```javascript
   // Check current context
   console.log(tooltipSystem.getCurrentContext());
   
   // Test context switching
   tooltipSystem.setContext('new_context');
   ```

3. **Content Validation**
   - Check tooltip content database
   - Verify content management system
   - Test with different user contexts

### Issue: Accessibility Features Not Working

**Symptoms:**
- Screen reader not announcing tooltips
- Keyboard navigation not working
- ARIA attributes missing

**Possible Causes:**
1. Accessibility features disabled
2. ARIA attributes not generated
3. Screen reader compatibility issues
4. Keyboard event handling problems

**Resolution Steps:**

1. **Enable Accessibility Features**
   ```bash
   # Verify accessibility configuration
   echo $ACCESSIBILITY_FEATURES_ENABLED
   echo $SCREEN_READER_SUPPORT_ENABLED
   ```

2. **Test ARIA Attributes**
   ```javascript
   // Check ARIA attributes
   const element = document.getElementById('tooltip-element');
   console.log(element.getAttribute('aria-describedby'));
   console.log(element.getAttribute('aria-label'));
   ```

3. **Keyboard Navigation Test**
   - Test Tab navigation through tooltips
   - Verify Enter/Space key activation
   - Check Escape key dismissal

## Prerequisite Validation Issues

### Issue: Prerequisites Always Failing

**Symptoms:**
- All prerequisite checks report failures
- Operations blocked unnecessarily
- False positive error messages

**Possible Causes:**
1. Service connectivity issues
2. Overly strict validation criteria
3. Network timeouts
4. Configuration problems

**Resolution Steps:**

1. **Check Service Connectivity**
   ```bash
   # Test Ollama connectivity
   curl -f http://localhost:11434/api/health
   
   # Test database connectivity
   pg_isready -h localhost -p 5432 -U gitte
   
   # Test Redis connectivity
   redis-cli ping
   ```

2. **Adjust Validation Criteria**
   ```yaml
   # In configuration
   prerequisite_validation:
     timeout_seconds: 30
     retry_attempts: 3
     strict_mode: false
   ```

3. **Network Debugging**
   - Check firewall settings
   - Verify DNS resolution
   - Test with different network connection

### Issue: Prerequisite Checks Too Slow

**Symptoms:**
- Long delays before operations start
- Timeout errors during validation
- Poor user experience

**Possible Causes:**
1. Network latency
2. Service overload
3. Inefficient validation logic
4. Cache not working

**Resolution Steps:**

1. **Enable Caching**
   ```bash
   # Verify cache configuration
   echo $PREREQUISITE_CACHE_TTL_SECONDS
   
   # Check cache hit rate
   redis-cli info stats | grep keyspace_hits
   ```

2. **Optimize Validation**
   ```python
   # Parallel validation
   async def validate_prerequisites():
       tasks = [
           validate_ollama(),
           validate_database(),
           validate_consent()
       ]
       results = await asyncio.gather(*tasks)
       return results
   ```

3. **Monitor Performance**
   - Check validation timing metrics
   - Identify slow prerequisite checks
   - Optimize or parallelize slow checks

## Accessibility Feature Problems

### Issue: High Contrast Mode Not Working

**Symptoms:**
- Colors don't change in high contrast mode
- Poor visibility for users with visual impairments
- Contrast ratios below WCAG standards

**Possible Causes:**
1. CSS not loading properly
2. Browser compatibility issues
3. Theme conflicts
4. JavaScript errors

**Resolution Steps:**

1. **Verify CSS Loading**
   ```javascript
   // Check if high contrast CSS is loaded
   const stylesheets = document.styleSheets;
   for (let sheet of stylesheets) {
       console.log(sheet.href);
   }
   ```

2. **Test Contrast Ratios**
   ```javascript
   // Calculate contrast ratio
   function getContrastRatio(color1, color2) {
       // Implementation to check WCAG compliance
       return ratio;
   }
   ```

3. **Browser Testing**
   - Test across different browsers
   - Check browser accessibility settings
   - Verify CSS custom properties support

### Issue: Keyboard Navigation Problems

**Symptoms:**
- Tab navigation skips elements
- Focus indicators not visible
- Keyboard shortcuts not working

**Possible Causes:**
1. Incorrect tabindex values
2. Focus management issues
3. Event handler problems
4. CSS focus styles missing

**Resolution Steps:**

1. **Fix Tab Order**
   ```html
   <!-- Ensure proper tabindex -->
   <button tabindex="0">Accessible Button</button>
   <div tabindex="-1">Not in tab order</div>
   ```

2. **Add Focus Styles**
   ```css
   /* Visible focus indicators */
   button:focus {
       outline: 2px solid #0066cc;
       outline-offset: 2px;
   }
   ```

3. **Test Keyboard Navigation**
   - Use only keyboard to navigate
   - Verify all interactive elements are reachable
   - Test with screen reader software

## Performance Issues

### Issue: Slow Application Response

**Symptoms:**
- Long loading times
- Delayed UI interactions
- High CPU/memory usage

**Possible Causes:**
1. Inefficient caching
2. Memory leaks
3. Unoptimized database queries
4. Large image processing

**Resolution Steps:**

1. **Monitor System Resources**
   ```bash
   # Check memory usage
   free -h
   
   # Check CPU usage
   top -p $(pgrep -f gitte)
   
   # Check disk I/O
   iostat -x 1
   ```

2. **Optimize Caching**
   ```bash
   # Check cache hit rates
   redis-cli info stats
   
   # Monitor cache memory usage
   redis-cli info memory
   ```

3. **Database Optimization**
   ```sql
   -- Check slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

### Issue: Memory Leaks

**Symptoms:**
- Gradually increasing memory usage
- Application becomes unresponsive
- System runs out of memory

**Possible Causes:**
1. Unclosed database connections
2. Cached objects not released
3. Event listeners not removed
4. Large objects in memory

**Resolution Steps:**

1. **Monitor Memory Usage**
   ```python
   import psutil
   import os
   
   process = psutil.Process(os.getpid())
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
   ```

2. **Fix Resource Leaks**
   ```python
   # Proper resource management
   try:
       with get_database_session() as session:
           # Database operations
           pass
   finally:
       # Cleanup resources
       cleanup_resources()
   ```

3. **Cache Management**
   ```python
   # Implement cache size limits
   cache.set_max_size(100 * 1024 * 1024)  # 100MB limit
   cache.set_eviction_policy('LRU')
   ```

## Deployment and Configuration Issues

### Issue: Docker Container Startup Failures

**Symptoms:**
- Containers fail to start
- Service dependency errors
- Configuration validation failures

**Possible Causes:**
1. Missing environment variables
2. Port conflicts
3. Volume mount issues
4. Network configuration problems

**Resolution Steps:**

1. **Check Environment Variables**
   ```bash
   # Verify all required variables are set
   docker-compose config
   
   # Check specific service configuration
   docker-compose logs gitte-app
   ```

2. **Resolve Port Conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8501
   
   # Kill conflicting processes
   sudo fuser -k 8501/tcp
   ```

3. **Fix Volume Mounts**
   ```bash
   # Check volume permissions
   ls -la ./config
   
   # Fix permissions if needed
   sudo chown -R 1000:1000 ./config
   ```

### Issue: Configuration Validation Errors

**Symptoms:**
- Application fails to start
- Invalid configuration messages
- Feature flags not working

**Possible Causes:**
1. Incorrect configuration format
2. Missing required settings
3. Invalid values
4. Environment variable conflicts

**Resolution Steps:**

1. **Validate Configuration**
   ```python
   # Run configuration validation
   python -m config.validation
   ```

2. **Check Required Settings**
   ```yaml
   # Ensure all required settings are present
   required_settings:
     - POSTGRES_DSN
     - OLLAMA_URL
     - SECRET_KEY
     - ENCRYPTION_KEY
   ```

3. **Fix Environment Variables**
   ```bash
   # Create .env file with correct values
   cat > .env << EOF
   POSTGRES_PASSWORD=secure_password
   SECRET_KEY=your_secret_key_here
   ENCRYPTION_KEY=your_encryption_key_here
   EOF
   ```

## Browser Compatibility Issues

### Issue: Features Not Working in Specific Browsers

**Symptoms:**
- Functionality works in some browsers but not others
- JavaScript errors in certain browsers
- CSS rendering issues

**Possible Causes:**
1. Browser API compatibility
2. CSS feature support
3. JavaScript version differences
4. Security policy restrictions

**Resolution Steps:**

1. **Check Browser Support**
   ```javascript
   // Feature detection
   if ('IntersectionObserver' in window) {
       // Use modern API
   } else {
       // Fallback implementation
   }
   ```

2. **Add Polyfills**
   ```html
   <!-- Add polyfills for older browsers -->
   <script src="https://polyfill.io/v3/polyfill.min.js"></script>
   ```

3. **CSS Fallbacks**
   ```css
   /* Provide fallbacks for newer CSS features */
   .container {
       display: block; /* Fallback */
       display: grid; /* Modern browsers */
   }
   ```

### Issue: Mobile Browser Problems

**Symptoms:**
- Touch interactions not working
- Layout issues on mobile
- Performance problems on mobile devices

**Possible Causes:**
1. Touch event handling
2. Viewport configuration
3. Mobile-specific CSS issues
4. Performance optimization needed

**Resolution Steps:**

1. **Fix Touch Events**
   ```javascript
   // Handle both mouse and touch events
   element.addEventListener('touchstart', handleTouch);
   element.addEventListener('mousedown', handleMouse);
   ```

2. **Optimize Viewport**
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   ```

3. **Mobile CSS**
   ```css
   @media (max-width: 768px) {
       .tooltip {
           font-size: 16px; /* Prevent zoom on iOS */
           touch-action: manipulation;
       }
   }
   ```

## System Integration Problems

### Issue: External Service Integration Failures

**Symptoms:**
- Ollama service not responding
- Database connection failures
- Redis cache not working

**Possible Causes:**
1. Service not running
2. Network connectivity issues
3. Authentication problems
4. Configuration mismatches

**Resolution Steps:**

1. **Check Service Status**
   ```bash
   # Check all services
   docker-compose ps
   
   # Check specific service logs
   docker-compose logs ollama
   docker-compose logs postgres
   docker-compose logs redis
   ```

2. **Test Connectivity**
   ```bash
   # Test Ollama
   curl http://localhost:11434/api/health
   
   # Test PostgreSQL
   psql -h localhost -U gitte -d kiro_test -c "SELECT 1;"
   
   # Test Redis
   redis-cli ping
   ```

3. **Fix Network Issues**
   ```bash
   # Restart networking
   docker-compose down
   docker network prune
   docker-compose up -d
   ```

## Getting Additional Help

### Log Collection

When reporting issues, collect relevant logs:

```bash
# Application logs
docker-compose logs gitte-app > app.log

# System logs
journalctl -u docker > system.log

# Browser console logs
# (Copy from browser developer tools)
```

### System Information

Include system information with issue reports:

```bash
# System info
uname -a
docker --version
docker-compose --version

# Resource usage
free -h
df -h
```

### Support Channels

1. **Documentation**: Check the complete user guide
2. **GitHub Issues**: Report bugs and feature requests
3. **Community Forum**: Get help from other users
4. **Support Email**: Contact technical support team

### Emergency Procedures

If the system becomes completely unresponsive:

1. **Safe Restart**
   ```bash
   docker-compose down
   docker system prune -f
   docker-compose up -d
   ```

2. **Reset to Defaults**
   ```bash
   # Backup current configuration
   cp docker-compose.yml docker-compose.yml.backup
   
   # Reset to default configuration
   git checkout docker-compose.yml
   ```

3. **Data Recovery**
   ```bash
   # Backup data volumes
   docker run --rm -v gitte_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
   ```

Remember to always backup your data before making significant changes to the system configuration.