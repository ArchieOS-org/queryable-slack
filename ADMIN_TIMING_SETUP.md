# Admin Job Timing Analysis Setup

## ✅ What Was Created

1. **admin_job_timing_prompt.xml** - Comprehensive XML prompt for analyzing admin job completion times
2. **Updated conductor/ask.py** - Added thinking mode support with Context7-guided reasoning
3. **CLI Flag** - Added `--thinking` flag to enable chain-of-thought reasoning

## 🎯 Features

### Thinking Mode
- **Chain-of-thought reasoning** - Breaks down complex questions into logical steps
- **Structured analysis** - Follows a 4-phase approach:
  1. Context Gathering
  2. Time Analysis
  3. Pattern Recognition
  4. Reporting

### Enhanced System Prompt
The thinking mode uses an enhanced system prompt that:
- Guides Claude through structured reasoning steps
- Encourages step-by-step analysis
- Considers multiple factors (urgency, complexity, workload)
- Requires specific citations with dates, channels, and admin names

## 📝 Usage

### Basic Query
```bash
python -m conductor.ask "How long does it take admins to complete tasks?" --db-path conductor_db
```

### With Thinking Mode (Recommended for Complex Analysis)
```bash
python -m conductor.ask "How long does it take admins to complete tasks?" --db-path conductor_db --thinking
```

### Full Featured Query
```bash
python -m conductor.ask "How long does it typically take admins to complete tasks like deal processing, broker loading, or updating contact lists? Show me specific examples with timestamps." --db-path conductor_db --hybrid --thinking --metrics
```

## 🔍 Query Examples

### Task Completion Time Analysis
```bash
python -m conductor.ask "How long does it typically take admins to process deal paperwork and add it to SkySlope?" --db-path conductor_db --thinking
```

### Turnaround Time Analysis
```bash
python -m conductor.ask "What is the typical turnaround time for preliminary broker loading (first draft creation)?" --db-path conductor_db --thinking
```

### Urgency vs Standard Requests
```bash
python -m conductor.ask "How quickly do admins respond to urgent requests versus standard requests?" --db-path conductor_db --thinking
```

## 📊 Admin Task Categories Analyzed

1. **Listing Tasks**
   - Deal Processing (paperwork to SkySlope, payment follow-up)
   - Preliminary Broker Loading (first draft creation)
   - Brokerbay Management (showing instructions, LBX instructions)
   - Media Kit Email (sending to clients)

2. **Firm Listing Tasks**
   - Updating the Boards (status changes)
   - Gift Coordination & Delivery
   - Post-Transaction Client Concierge

3. **Client File Management**
   - Google Drive organization
   - Deal folder organization
   - Document management

4. **Contact & CRM Management**
   - Contact list updates (Excel and Chime)
   - Property alert setup
   - Database maintenance

5. **Communication Tasks**
   - Slack channel posting (transaction announcements)
   - Follow-up communications
   - Meeting coordination

## 🧠 Thinking Framework

The prompt uses a 5-step reasoning framework:

1. **Identify task request patterns** - How are tasks requested?
2. **Identify completion indicators** - What language indicates completion?
3. **Calculate time intervals** - Measure request to completion
4. **Analyze patterns** - Which tasks take longest/fastest?
5. **Synthesize findings** - What are typical completion times?

## 📈 Example Output Structure

The thinking mode produces structured responses with:

- **Summary** - High-level overview
- **Methodology** - How analysis was conducted
- **Findings by Category** - Breakdown by task type
- **Patterns** - Identified trends
- **Factors** - What affects completion time
- **Examples** - Specific examples with timestamps

## ⚙️ Configuration

### Thinking Mode Parameters
- **Model**: `claude-sonnet-4-5-20250929`
- **Max Tokens**: 2048 (increased from 1024 for detailed reasoning)
- **Temperature**: 0.3 (lower for focused reasoning)
- **System Prompt**: Enhanced with structured thinking instructions

### Context7 Integration
- Uses Context7 documentation for optimal thinking patterns
- Applies chain-of-thought reasoning best practices
- Structures complex analysis tasks effectively

## 🎉 Benefits

- ✅ **Structured Analysis** - Step-by-step reasoning process
- ✅ **Better Accuracy** - Considers multiple factors
- ✅ **Clear Citations** - Specific dates, channels, admin names
- ✅ **Pattern Recognition** - Identifies trends and outliers
- ✅ **Context Awareness** - Accounts for urgency, complexity, workload

## 📚 Related Files

- `admin_job_timing_prompt.xml` - Full prompt specification
- `conductor/ask.py` - Implementation with thinking mode support
- `CONTEXT7_SETUP.md` - Context7 configuration guide

## 🔄 Future Enhancements

- Add support for explicit thinking tokens when available in API
- Create specialized prompts for different task categories
- Add visualization of completion time patterns
- Integrate with monitoring/metrics for real-time analysis

