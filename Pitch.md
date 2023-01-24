# Problems

- My first contribution at team Nova, I make a PR see the pipelines pass, and merge, the next day we are alerted that
    my PR was reverted, and that Pipeline xyz should have been tested beforehand, funny enough the bug I was fixing 
    had also been reverted due to a pipeline that fails downstream.

  - Nobody can keep a track of what pipelines trigger what unless they  have been working on this project for an extensive
      period of time and have tribal knowledge.
    -     Why not just have documentation? -> Because non auto-generated documentation gets outdated.

  - There's no coherent way to track the indirectly dependent pipelines that should succeed before we hit merge.


- Another issue was the amount of time wasted for a pipeline sage to complete only to find out a pipeline failed to trigger.
    Pipelines that are set to trigger the next pipeline will often fail silently in the trigger step.
  

- During development of onboarding reservoir DDMS into  I often had to ask hey what pipeline does a particular file 
define? The only two ways to solve this
 question was brute force linear search through all pipelines in ADO or ask around and trust my fellow engineers that 
  they know it all.
