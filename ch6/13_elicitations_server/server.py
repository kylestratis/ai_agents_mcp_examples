from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

# Initialize FastMCP server
mcp = FastMCP("elicitations-server")

# Form schema for elicitation requests
FORM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "title": "Full Name",
            "description": "Your full name",
            "minLength": 1,
        },
        "email": {
            "type": "string",
            "title": "Email Address",
            "description": "Your email address",
            "format": "email",
        },
        "age": {
            "type": "number",
            "title": "Age",
            "description": "Your age in years",
            "minimum": 0,
            "maximum": 150,
        },
    },
    "required": ["name", "email"],
}


@mcp.tool()
async def signup_math_facts(ctx: Context[ServerSession, None]) -> str:
    """Sign up to receive daily math facts (demonstration of elicitation)."""
    # Make elicitation request to collect user information
    try:
        elicit_result = await ctx.session.elicit(
            message="Please provide your information to sign up for daily math facts!",
            requestedSchema=FORM_SCHEMA,
        )
    except Exception as e:
        await ctx.error(f"Error during math facts signup: {str(e)}")
        return f"Sorry, there was an error during signup: {str(e)}"

    await ctx.debug(f"Elicitation result: {elicit_result}")

    # Handle the different response actions
    if elicit_result.action == "accept":
        user_data = elicit_result.content
        await ctx.info(f"User signed up: {user_data}")

        # Extract user information
        name = user_data["name"]
        email = user_data["email"]
        age = user_data.get("age")

        response = (
            f"Welcome {name}! You've successfully signed up for daily math facts.\n"
        )
        response += f"We'll send interesting mathematical tidbits to {email}.\n"

        if age:
            response += (
                f"Thanks for sharing that you're {age} years old - "
                "we'll tailor the content accordingly!\n"
            )

        response += "\nYou'll receive your first math fact soon!"
        response += (
            "\n(Note: This is just a demonstration - no actual signup occurred!)"
        )

        return response

    elif elicit_result.action == "decline":
        await ctx.info("User declined math facts signup")
        return (
            "No problem! You've chosen not to sign up for math facts. "
            "You can always use our calculation tools anytime!"
        )

    elif elicit_result.action == "cancel":
        await ctx.info("User cancelled math facts signup")
        return (
            "Signup cancelled. Feel free to try again later or "
            "use our other mathematical tools!"
        )

    else:
        await ctx.warning(f"Unexpected elicitation action: {elicit_result.action}")
        return "Something unexpected happened during signup. Please try again."


if __name__ == "__main__":
    mcp.run()
