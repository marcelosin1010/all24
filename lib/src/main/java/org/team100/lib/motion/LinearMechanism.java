package org.team100.lib.motion;

import java.util.OptionalDouble;

import org.team100.lib.encoder.IncrementalBareEncoder;
import org.team100.lib.motor.BareMotor;

/**
 * Uses a motor, gears, and a wheel to produce linear output, e.g. a drive wheel
 * or conveyor belt.
 */
public class LinearMechanism {
    private final BareMotor m_motor;
    private final IncrementalBareEncoder m_encoder;
    private final double m_gearRatio;
    private final double m_wheelRadiusM;

    public LinearMechanism(
            BareMotor motor,
            IncrementalBareEncoder encoder,
            double gearRatio,
            double wheelDiameterM) {
        m_motor = motor;
        m_encoder = encoder;
        m_gearRatio = gearRatio;
        m_wheelRadiusM = wheelDiameterM / 2;
    }

    public void setDutyCycle(double output) {
        m_motor.setDutyCycle(output);
    }

    public void setVelocity(
            double outputVelocityM_S,
            double outputAccelM_S2,
            double outputForceN) {
        m_motor.setVelocity(
                (outputVelocityM_S / m_wheelRadiusM) * m_gearRatio,
                (outputAccelM_S2 / m_wheelRadiusM) * m_gearRatio,
                outputForceN * m_wheelRadiusM / m_gearRatio);
    }

    public void setPosition(
            double outputPositionM,
            double outputVelocityM_S,
            double outputForceN) {
        m_motor.setPosition(
                (outputPositionM / m_wheelRadiusM) * m_gearRatio,
                (outputVelocityM_S / m_wheelRadiusM) * m_gearRatio,
                outputForceN * m_wheelRadiusM / m_gearRatio);
    }

    public OptionalDouble getVelocityM_S() {
        OptionalDouble velocityRad_S = m_encoder.getVelocityRad_S();
        if (velocityRad_S.isEmpty())
            return OptionalDouble.empty();
        return OptionalDouble.of(velocityRad_S.getAsDouble() * m_wheelRadiusM / m_gearRatio);
    }

    public OptionalDouble getPositionM() {
        OptionalDouble positionRad = m_encoder.getPositionRad();
        if (positionRad.isEmpty())
            return OptionalDouble.empty();
        return OptionalDouble.of(positionRad.getAsDouble() * m_wheelRadiusM / m_gearRatio);
    }

    public void stop() {
        m_motor.stop();
    }

    public void close() {
        m_motor.close();
        m_encoder.close();
    }

    public void resetEncoderPosition() {
        m_encoder.reset();
    }

}