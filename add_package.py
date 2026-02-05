#!/usr/bin/env python3
"""
Script to add Supabase Swift Package to Xcode project
"""
import uuid
import re

def generate_xcode_uuid():
    """Generate a 24-character hex string like Xcode UUIDs"""
    return uuid.uuid4().hex[:24].upper()

def add_supabase_package():
    pbxproj_path = "workout tracker app.xcodeproj/project.pbxproj"

    # Read the file
    with open(pbxproj_path, 'r') as f:
        content = f.read()

    # Generate UUIDs for new objects
    package_ref_uuid = generate_xcode_uuid()
    product_dep_uuid = generate_xcode_uuid()

    # Define the package reference
    package_reference = f"""
/* Begin XCRemoteSwiftPackageReference section */
		{package_ref_uuid} /* XCRemoteSwiftPackageReference "supabase-swift" */ = {{
			isa = XCRemoteSwiftPackageReference;
			repositoryURL = "https://github.com/supabase/supabase-swift";
			requirement = {{
				kind = upToNextMajorVersion;
				minimumVersion = 2.0.0;
			}};
		}};
/* End XCRemoteSwiftPackageReference section */
"""

    # Define the product dependency
    product_dependency = f"""
/* Begin XCSwiftPackageProductDependency section */
		{product_dep_uuid} /* Supabase */ = {{
			isa = XCSwiftPackageProductDependency;
			package = {package_ref_uuid} /* XCRemoteSwiftPackageReference "supabase-swift" */;
			productName = Supabase;
		}};
/* End XCSwiftPackageProductDependency section */
"""

    # Add package reference section before PBXProject section
    content = content.replace(
        "/* Begin PBXProject section */",
        package_reference + "\n/* Begin PBXProject section */"
    )

    # Add product dependency section before PBXProject section
    content = content.replace(
        "/* Begin PBXProject section */",
        product_dependency + "\n/* Begin PBXProject section */"
    )

    # Find the PBXProject section and add packageReferences
    project_pattern = r'(E28F4C792F265358002B94F9 /\* Project object \*/ = \{[^}]+?targets = \([^)]+\);)'
    def add_package_refs(match):
        return match.group(1) + f'\n\t\t\tpackageReferences = (\n\t\t\t\t{package_ref_uuid} /* XCRemoteSwiftPackageReference "supabase-swift" */,\n\t\t\t);'

    content = re.sub(project_pattern, add_package_refs, content, flags=re.DOTALL)

    # Find the main target and add packageProductDependencies
    target_pattern = r'(E28F4C802F265359002B94F9 /\* workout tracker app \*/ = \{[^}]+?productReference = [^;]+;)'
    def add_product_deps(match):
        return match.group(1) + f'\n\t\t\tpackageProductDependencies = (\n\t\t\t\t{product_dep_uuid} /* Supabase */,\n\t\t\t);'

    content = re.sub(target_pattern, add_product_deps, content, flags=re.DOTALL)

    # Write the modified content
    with open(pbxproj_path, 'w') as f:
        f.write(content)

    print(f"✅ Successfully added Supabase package")
    print(f"Package Reference UUID: {package_ref_uuid}")
    print(f"Product Dependency UUID: {product_dep_uuid}")
    print("\nNext steps:")
    print("1. Open Xcode")
    print("2. Xcode will resolve the package automatically")
    print("3. Build the project (⌘B)")

if __name__ == "__main__":
    add_supabase_package()
