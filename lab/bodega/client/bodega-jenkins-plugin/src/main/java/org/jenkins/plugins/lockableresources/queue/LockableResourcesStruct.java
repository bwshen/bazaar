/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
 * Copyright (c) 2013, Aki Asikainen. All rights reserved.             *
 *                                                                     *
 * This file is part of the Jenkins Lockable Resources Plugin and is   *
 * published under the MIT license.                                    *
 *                                                                     *
 * See the "LICENSE.txt" file for more information.                    *
 * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
package org.jenkins.plugins.lockableresources.queue;

import hudson.EnvVars;

import java.util.ArrayList;
import java.util.List;

import org.jenkins.plugins.lockableresources.LockableResource;
import org.jenkins.plugins.lockableresources.LockableResourcesManager;
import org.jenkins.plugins.lockableresources.RequiredResourcesProperty;

public class LockableResourcesStruct {
    /** A list containing the global resources that may be required by a job */
    public List<LockableResource> required;
    /** A YAML string describing Bodega item requirements */
    public String bodegaItemRequirements;
    /** The labels associated with the required resources */
    public String label;
    /** The name of the variable that will hold the required resources names */
    public String requiredVar;
    /** The number of resources required */
    public String requiredNumber;

    public LockableResourcesStruct(RequiredResourcesProperty property,
                                   EnvVars env) {
        required = new ArrayList<LockableResource>();
        for (String name : property.getResources()) {
            LockableResource r =
                LockableResourcesManager.get().fromName(env.expand(name));
            if (r != null) {
                this.required.add(r);
            }
        }

        bodegaItemRequirements = env.expand(
            property.getBodegaItemRequirements());
        if (bodegaItemRequirements == null)
            bodegaItemRequirements = "";


        label = env.expand(property.getLabelName());
        if (label == null)
            label = "";
        requiredVar = property.getResourceNamesVar();
        requiredNumber = property.getResourceNumber();
        if (requiredNumber != null && requiredNumber.equals("0"))
            requiredNumber = null;
    }

    public String toString() {
        return "Required resources: " + this.required +
            ", Required label: " + this.label +
            ", Variable name: " + this.requiredVar +
            ", Number of resources: " + this.requiredNumber +
            ", Bodega item requirements: " + this.bodegaItemRequirements;
    }

    public int getRequiredNumber() {
        try {
            return Integer.parseInt(this.requiredNumber);
        } catch (NumberFormatException e) {
            return 0;
        }
    }
}
