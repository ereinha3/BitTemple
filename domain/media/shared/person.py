class CastMember(BaseModel):
    """A cast member in a movie."""
    
    name: str = Field(..., description="Actor's name")
    character: str = Field(..., description="Character name")
    order: int = Field(..., description="Billing order (0 = top billed)")
    profile_path: Optional[str] = Field(None, description="Profile image path")


class CrewMember(BaseModel):
    """A crew member in a movie."""
    
    name: str = Field(..., description="Crew member's name")
    job: str = Field(..., description="Job title (Director, Writer, etc.)")
    department: str = Field(..., description="Department (Directing, Writing, etc.)")