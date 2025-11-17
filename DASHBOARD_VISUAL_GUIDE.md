# Dashboard Visual Guide - Before & After

## What Changed: Node Detail Sidebar

### BEFORE (Old Layout)
```
┌─────────────────────────────────────┐
│ Node Details                    [×] │
├─────────────────────────────────────┤
│ Question                            │
│ Which country is going to win...   │
├─────────────────────────────────────┤
│ Metadata                            │
│ Status: complete | Depth: 0         │
│ Answerable: No                      │
├─────────────────────────────────────┤
│ Literature Writeup                  │  ← Generic heading
│                                     │
│ # Global Leadership in AI...        │
│ The unfolding global competition... │
│ [content continues...]              │
├─────────────────────────────────────┤
│ Subtasks (9)                        │
│ • What are key factors...           │
│ • China's specific AI investments.. │
│ [more subtasks...]                  │
├─────────────────────────────────────┤
│ Children Nodes (9)                  │
│ [buttons to navigate to children]   │
└─────────────────────────────────────┘
```

**Problem:** 
- No visibility of the final report
- Unclear when literature writeup was generated
- Missing key synthesis information

---

### AFTER (New Layout)
```
┌─────────────────────────────────────┐
│ Node Details                    [×] │
├─────────────────────────────────────┤
│ Question                            │
│ Which country is going to win...   │
├─────────────────────────────────────┤
│ Metadata                            │
│ Status: complete | Depth: 0         │
│ Answerable: No                      │
├─────────────────────────────────────┤
│ LITERATURE WRITEUP (BEFORE SUBTASKS)│  ← NEW: Clear timing label
│ ┌─────────────────────────────────┐ │
│ │ Initial research synthesis from │ │  ← NEW: Explanation box
│ │ literature search, generated    │ │
│ │ before decomposing into subtasks│ │
│ └─────────────────────────────────┘ │
│                                     │
│ # Global Leadership in AI...        │
│ The unfolding global competition... │
│ [content continues...]              │
├─────────────────────────────────────┤
│ Subtasks (9)                        │
│ • What are key factors...           │
│ • China's specific AI investments.. │
│ [more subtasks...]                  │
├─────────────────────────────────────┤
│ FINAL REPORT (AFTER SUBTASKS        │  ← NEW: Entirely new section!
│ COMPLETE)                           │
│ ┌─────────────────────────────────┐ │
│ │ Polished, structured report     │ │  ← NEW: Explanation box
│ │ synthesized after all child     │ │
│ │ nodes completed exploration.    │ │
│ │ Includes key insights, thesis,  │ │
│ │ and comprehensive findings.     │ │
│ └─────────────────────────────────┘ │
│                                     │
│ # United States and China Lead...   │
│ ## Global Overview of AI Arms Race  │
│ The global artificial intelligence  │
│ [content continues with polished    │
│  narrative, thesis, and synthesis]  │
├─────────────────────────────────────┤
│ Children Nodes (9)                  │
│ [buttons to navigate to children]   │
└─────────────────────────────────────┘
```

**Benefits:**
✅ Both reports now visible
✅ Clear timing indicators (Before vs After)
✅ Explanatory descriptions for context
✅ Better understanding of pipeline flow

---

## Pipeline Visualization

```
Research Node Exploration Process:

┌─────────────────────────────────────────────────────────────┐
│                     START: _explore_node()                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Literature     │
                  │ Search         │
                  └───────┬────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ node.literature_writeup│ ◄─── 📝 SHOWN in "Before Subtasks"
              │ = "Initial synthesis" │
              └───────────┬───────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Is Answerable? │
                  │ Check          │
                  └───────┬────────┘
                          │
                          ▼
                  ┌────────────────┐
                  │ Generate       │
                  │ Subtasks       │
                  └───────┬────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ Recursively Explore   │
              │ Each Child Node       │
              │                       │
              │  ┌──► child_1         │
              │  ├──► child_2         │
              │  ├──► child_3         │
              │  └──► ...             │
              └───────────┬───────────┘
                          │
                    [ALL CHILDREN
                     COMPLETE]
                          │
                          ▼
                  ┌────────────────┐
                  │ Generate       │
                  │ Final Report   │
                  └───────┬────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ node.report =         │ ◄─── 📝 SHOWN in "After Subtasks"
              │ "Polished report with │
              │  thesis & insights"   │
              └───────────┬───────────┘
                          │
                          ▼
                ┌──────────────────┐
                │ Node Complete    │
                └──────────────────┘
```

---

## Key Differences Between Reports

### Literature Writeup (Before Subtasks)
- **Timing**: Generated immediately after literature search
- **Content**: Direct synthesis of web search results
- **Purpose**: Initial understanding of the topic
- **Style**: Factual compilation with citations
- **Example Start**: "# Global Leadership in the AI Arms Race"

### Final Report (After Subtasks Complete)
- **Timing**: Generated after all child nodes finish
- **Content**: Polished narrative with key insights extracted
- **Purpose**: Comprehensive answer incorporating deeper research
- **Style**: Structured with thesis, thematic sections, strategic analysis
- **Example Start**: "# United States and China Lead Global AI Arms Race Amid Strategic National Rivalries"

---

## How to Use

1. **Start Dashboard** (if not already running):
   ```bash
   cd dashboard/frontend
   npm run dev
   ```

2. **View a Run**:
   - Open http://localhost:5173
   - Click on any completed run
   - Click on a node in the graph visualization

3. **Compare Reports**:
   - Scroll through the sidebar
   - Read "Literature Writeup (Before Subtasks)" first
   - Then read "Final Report (After Subtasks Complete)"
   - Notice how the final report is more polished and structured

4. **Understand the Pipeline**:
   - The descriptions explain when each report is generated
   - You can now see the full research progression
   - Great for debugging or understanding how synthesis works

---

## Technical Details

**Files Changed:**
- `dashboard/frontend/src/components/RunDetail.jsx` (2 sections modified)
- `dashboard/frontend/src/components/RunDetail.css` (1 new style added)

**Data Source:**
- Both fields already exist in `ResearchNode` dataclass
- No backend changes needed
- Fully backward compatible

**Styling:**
- Blue left border for description boxes
- Italicized explanatory text
- Consistent with existing dashboard theme

